// Exercise state transitions and cancellation in a real local browser.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import puppeteer from 'puppeteer';
const root = path.resolve(process.argv[2]);
const server = createServer(async (req,res) => {
  const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\/nrpe-custom(?=\/)/, '');
  const file = path.resolve(root, '.' + (pathname.endsWith('/') ? pathname+'index.html' : pathname));
  if (!file.startsWith(root+path.sep)) {res.writeHead(403).end();return;}
  try {
    const data=await readFile(file);
    res.setHeader('Content-Type', file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':file.endsWith('.woff2')?'font/woff2':'application/octet-stream');
    res.end(data);
  } catch {res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try {
  browser=await puppeteer.launch({executablePath:process.env.NRPE_WEBSITE_BROWSER,headless:true,args:['--no-sandbox']});
  const page=await browser.newPage();const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/nrpe-custom/`,{waitUntil:'networkidle0'});
  await page.waitForSelector('[data-terminal-demo]:not([hidden])');
  const text=()=>page.$eval('[data-demo-output]',e=>e.textContent);
  const command=async value=>{
    await page.$eval('[data-demo-input]',(e,value)=>{e.value=value;},value);
    await page.$eval('[data-demo-form]',e=>e.requestSubmit());
  };
  await page.focus('[data-demo-command="verify"]');await page.keyboard.press('ArrowDown');
  assert.equal(await page.evaluate(()=>document.activeElement.dataset.demoCommand),'status');
  await page.keyboard.press('Enter');assert.match(await text(),/not built/);
  await command('python3 nrpe.py verify debian12');
  await page.waitForSelector('[data-demo-cancel]:not([disabled])');
  await page.keyboard.press('Escape');await new Promise(resolve=>setTimeout(resolve,650));
  await command('status');assert.doesNotMatch(await text(),/sample package present/);
  await command('verify debian12');
  await page.waitForFunction(()=>document.querySelector('[data-demo-phase]').textContent==='Demo complete');
  await command('verify debian12');await page.waitForSelector('[data-demo-confirm]:not([hidden])');
  await page.click('[data-demo-no]');assert.match(await text(),/Demo data retained/);
  await command('clean');assert.match(await text(),/2 sample expired reports/);
  await command('clean --apply');await page.waitForSelector('[data-demo-confirm]:not([hidden])');
  await page.click('[data-demo-yes]');await command('status');assert.match(await text(),/sample package present/);
  await command('clean');assert.match(await text(),/0 sample expired reports/);
  await command('<img src=x onerror=alert(1)>');assert.equal(await page.$$eval('[data-terminal-demo] img',e=>e.length),0);
  await page.click('[data-demo-reset]');assert.doesNotMatch(await text(),/sample package present/);
  await page.setViewport({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);
} finally {await browser?.close();await new Promise(resolve=>server.close(resolve));}
