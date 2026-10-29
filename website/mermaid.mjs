// A loopback-only build page; no runtime renderer is shipped to the website.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';

process.stdin.setEncoding('utf8');
let input = '';
for await (const chunk of process.stdin) input += chunk;
const { source, config, browser: executablePath } = JSON.parse(input);
const root = resolve(dirname(fileURLToPath(import.meta.url)), 'node_modules/mermaid/dist');
const server = createServer(async (request, response) => {
  try {
    const path = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (path === '/') {
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end('<!doctype html><html><body><div id="diagram"></div><script type="module">'
        + 'import mermaid from "/mermaid/mermaid.esm.min.mjs";'
        + 'window.renderDiagram=async(source,config)=>{mermaid.initialize(config);'
        + 'return (await mermaid.render("nrpe-diagram",source)).svg;};'
        + '</script></body></html>');
      return;
    }
    if (!path.startsWith('/mermaid/')) throw new Error('Unknown build asset');
    const file = resolve(root, path.slice('/mermaid/'.length));
    if (!file.startsWith(root + sep)) throw new Error('Invalid asset path');
    const data = await readFile(file);
    response.writeHead(200, { 'Content-Type': file.endsWith('.json') ? 'application/json' : 'text/javascript' });
    response.end(data);
  } catch {
    response.writeHead(404);
    response.end();
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await puppeteer.launch({ executablePath, headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (request.url().startsWith(origin + '/')) request.continue();
    else request.abort();
  });
  await page.goto(origin, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => typeof window.renderDiagram === 'function');
  const svg = await page.evaluate(({ source, config }) => window.renderDiagram(source, config), { source, config });
  process.stdout.write(svg);
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
