// Browser behavior checks use the existing pinned Puppeteer and local static output.
import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, sep, extname } from 'node:path';
import puppeteer from 'puppeteer';

const root = resolve('.nrpe/site/nrpe-custom');
const results = resolve('.nrpe/browser-results');
let server, browser, origin;
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
before(async () => {
  await mkdir(results, { recursive: true });
  assert.ok(existsSync(resolve(root, 'site-manifest.json')), 'Build the website before browser tests');
  server = createServer(async (request, response) => {
    try {
      let name = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      if (!name.startsWith('/nrpe-custom/')) throw new Error('Unknown base path');
      name = name.slice('/nrpe-custom/'.length);
      if (!name || name.endsWith('/')) name += 'index.html';
      const file = resolve(root, name);
      if (!file.startsWith(root + sep)) throw new Error('Unsafe path');
      const bytes = await readFile(file);
      response.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
      response.end(bytes);
    } catch { response.writeHead(404); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  const executablePath = process.env.NRPE_WEBSITE_BROWSER || ['/usr/bin/chromium', '/usr/bin/google-chrome'].find(existsSync);
  assert.ok(executablePath, 'Set NRPE_WEBSITE_BROWSER to Chrome/Chromium');
  browser = await puppeteer.launch({ executablePath, headless: true, args: ['--no-sandbox'] });
});
after(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
});
async function check(name, run) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (request.url().startsWith(origin + '/') || request.url().startsWith('data:')) request.continue();
    else { errors.push('Unexpected external request: ' + request.url()); request.abort(); }
  });
  try {
    await run(page);
    assert.deepEqual(errors, [], 'No JS errors or external runtime assets');
  } catch (error) {
    await page.screenshot({ path: resolve(results, name + '.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally { await page.close(); }
}
const visit = (page, path = '') => page.goto(origin + '/nrpe-custom/' + path, { waitUntil: 'networkidle0' });
const noOverflow = page => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);

test('homepage and documents fit mobile, tablet and desktop', () => check('responsive', async page => {
  for (const width of [390, 768, 1440]) {
    await page.setViewport({ width, height: 900 });
    for (const route of ['', 'installation/', 'faq/']) {
      await visit(page, route);
      assert.ok(await noOverflow(page), `${route} fits ${width}px`);
      assert.equal(await page.$('script[src*="terminal-demo"]'), null);
    }
  }
}));

test('documentation navigation scrolls independently and reaches the footer', () => check('sidebar', async page => {
  await page.setViewport({ width: 1440, height: 800 });
  await visit(page, 'network/');
  await page.$$eval('.nav-group', nodes => nodes.forEach(node => { node.open = true; }));
  assert.ok(await page.$eval('.sidebar-content', e => e.scrollHeight > e.clientHeight));
  const start = await page.evaluate(() => scrollY);
  await page.hover('.sidebar-content');
  await page.mouse.wheel({ deltaY: 1000 });
  await page.waitForFunction(() => document.querySelector('.sidebar-content').scrollTop > 0);
  assert.equal(await page.evaluate(() => scrollY), start);
  for (const y of [0, 1000, 100000]) {
    await page.evaluate(y => scrollTo(0, y), y);
    assert.ok(await page.evaluate(() => Math.abs(document.querySelector('.sidebar').getBoundingClientRect().bottom
      - document.querySelector('.site-footer').getBoundingClientRect().top) < 2));
  }
  assert.ok(await page.$eval('.site-footer', e => e.getBoundingClientRect().height < 110));
  assert.equal(await page.$eval('.sidebar-content', e => getComputedStyle(e).scrollbarWidth), 'thin');
}));

test('field-note outline links track the last section and collapse on mobile', () => check('outline', async page => {
  await page.setViewport({ width: 1440, height: 900 });
  await visit(page, 'field-notes/sles12-handshake/');
  assert.ok(await page.$eval('.article-outline', e => e.open));
  const last = '.field-note-toc a[href="#outcome-and-limits"]';
  await page.click(last);
  await page.waitForFunction(() => document.querySelector('.field-note-toc a[aria-current="location"]')?.hash === '#outcome-and-limits');
  assert.ok(await page.$eval('.field-note-toc', e => e.getBoundingClientRect().top <= 80));
  await page.setViewport({ width: 390, height: 844 });
  await visit(page, 'field-notes/sles12-handshake/');
  assert.equal(await page.$eval('.article-outline', e => e.open), false);
  await page.click('.article-outline summary');
  await page.click(last);
  assert.equal(await page.evaluate(() => location.hash), '#outcome-and-limits');
  assert.ok(await noOverflow(page));
  await page.setJavaScriptEnabled(false);
  await visit(page, 'field-notes/sles12-handshake/');
  assert.ok(await page.$eval('.article-outline', e => e.open), 'No-JS links remain available');
}));

test('FAQ filters answers, reports no matches and supports keyboard clearing', () => check('faq', async page => {
  await visit(page, 'faq/');
  await page.type('#faq-filter', 'TLS');
  assert.ok(await page.$$eval('.faq-question:not([hidden])', nodes => nodes.length > 0));
  await page.$eval('#faq-filter', e => { e.value = 'unmatchable-faq-query'; e.dispatchEvent(new Event('input')); });
  assert.equal(await page.$eval('#faq-empty', e => e.hidden), false);
  await page.focus('#faq-clear');
  await page.keyboard.press('Enter');
  assert.equal(await page.$eval('#faq-filter', e => e.value), '');
  assert.ok(await page.$eval('#faq-filter', e => document.activeElement === e));
  assert.ok(await page.$$eval('.faq-question', nodes => nodes.every(e => !e.hidden)));
}));

test('documentation search and mobile navigation work from the keyboard', () => check('search', async page => {
  await visit(page, 'overview/');
  await page.keyboard.down('Control'); await page.keyboard.press('k'); await page.keyboard.up('Control');
  assert.ok(await page.$eval('#site-search', e => document.activeElement === e));
  await page.type('#site-search', 'Swap');
  await page.waitForSelector('#search-results a');
  assert.ok(await page.$$eval('#search-results a', nodes => nodes.every(e => e.pathname.startsWith('/nrpe-custom/'))));
  await page.keyboard.press('Escape');
  assert.ok(await page.$eval('#search-results', e => e.hidden));
  await page.setViewport({ width: 390, height: 844 });
  await visit(page, 'overview/');
  await page.focus('.docs-toggle');
  await page.keyboard.press('Enter');
  assert.equal(await page.$eval('.docs-toggle', e => e.getAttribute('aria-expanded')), 'true');
  await page.keyboard.press('Enter');
  assert.equal(await page.$eval('.docs-toggle', e => e.getAttribute('aria-expanded')), 'false');
}));


test('tall diagrams keep native size in a compact scrollable preview', () => check('diagram-size', async page => {
  for (const width of [1440, 390]) {
    await page.setViewport({ width, height: 900 });
    await visit(page, 'overview/');
    const geometry = await page.$eval('.diagram-viewport', element => {
      const image = element.querySelector('img');
      return { height: element.clientHeight, scrollHeight: element.scrollHeight,
        imageWidth: image.getBoundingClientRect().width,
        nativeWidth: Number(image.getAttribute('width')) };
    });
    assert.ok(geometry.height <= 560, 'Preview stays compact');
    assert.ok(geometry.scrollHeight > geometry.height, 'Full diagram remains scrollable');
    assert.ok(geometry.imageWidth <= geometry.nativeWidth + 1, 'Small SVG is not stretched');
    assert.ok(await noOverflow(page));
    assert.ok(await page.$eval('.diagram figcaption a', element => element.href.endsWith('.svg')));
    await page.focus('.diagram-viewport');
    await page.keyboard.press('ArrowDown');
    await page.waitForFunction(() => document.querySelector('.diagram-viewport').scrollTop > 0);
  }
}));

test('wide documents center their content and keep table words readable', () => check('wide-tables', async page => {
  for (const width of [1440, 1920, 3440]) {
    await page.setViewport({ width, height: width === 3440 ? 1440 : 1080 });
    for (const route of ['package-compatibility/', 'package-reviews/2026-10-30/']) {
      await visit(page, route);
      const geometry = await page.evaluate(() => {
        const table = document.querySelector('.prose table');
        const scroller = table.closest('.table-scroll');
        const content = document.querySelector('.document');
        const available = document.querySelector('.docs-layout').getBoundingClientRect();
        const sidebar = document.querySelector('.sidebar').getBoundingClientRect();
        const bounds = content.getBoundingClientRect();
        return { maxRowHeight: Math.max(...Array.from(table.rows, row => row.getBoundingClientRect().height)),
          scrollWidth: scroller.scrollWidth, clientWidth: scroller.clientWidth,
          articleWidth: document.querySelector('.document-main').getBoundingClientRect().width,
          documentWidth: bounds.width,
          leftSpace: bounds.left - sidebar.right, rightSpace: available.right - bounds.right };
      });
      assert.ok(await noOverflow(page), `${route} fits ${width}px`);
      assert.ok(geometry.scrollWidth <= geometry.clientWidth + 1, 'Evidence table fits without horizontal scrolling');
      assert.ok(geometry.maxRowHeight < 180, 'Rows avoid excessive height from fragmented words');
      if (width === 3440) {
        assert.ok(geometry.articleWidth >= 1100, 'Wide tables have useful space');
        assert.ok(geometry.documentWidth <= 1600, 'Reading area stays bounded');
        assert.ok(Math.abs(geometry.leftSpace - geometry.rightSpace) < 2, 'Document is centered beside navigation');
        assert.ok(geometry.leftSpace <= 24, 'Navigation stays close to the document on ultrawide displays');
      }
    }
  }
  await page.setViewport({ width: 390, height: 844 });
  await visit(page, 'package-compatibility/');
  assert.ok(await noOverflow(page), 'Matrix stays inside the mobile page');
}));


test('headers keep visible controls aligned from mobile to 4K', () => check('header-sizes', async page => {
  for (const width of [390, 768, 1440, 1920, 2560, 3440, 3840]) {
    await page.setViewport({ width, height: width === 3840 ? 2160 : 1080 });
    for (const route of ['', 'package-reviews/2026-10-30/', 'field-notes/']) {
      await visit(page, route);
      const geometry = await page.evaluate(() => {
        const header = document.querySelector('.site-header');
        const controls = [...header.querySelectorAll('a, input')].map(element => element.getBoundingClientRect())
          .filter(rect => rect.width && rect.height).sort((a, b) => a.left - b.left)
          .map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }));
        const docs = document.querySelector('.docs-layout');
        return { controls, docsLeft: docs?.getBoundingClientRect().left,
          brandLeft: header.querySelector('.brand').getBoundingClientRect().left };
      });
      assert.ok(await noOverflow(page), `${route} header fits ${width}px`);
      for (let index = 0; index < geometry.controls.length; index++) {
        const control = geometry.controls[index];
        assert.ok(control.left >= 0 && control.right <= width + 1, 'Visible header control stays on screen');
        for (const other of geometry.controls.slice(0, index)) {
          const overlapX = Math.min(control.right, other.right) - Math.max(control.left, other.left);
          const overlapY = Math.min(control.bottom, other.bottom) - Math.max(control.top, other.top);
          assert.ok(overlapX <= 1 || overlapY <= 1, 'Visible header controls do not overlap');
        }
      }
      if (width >= 1920 && geometry.docsLeft !== undefined) {
        assert.ok(Math.abs(geometry.brandLeft - geometry.docsLeft - 22) < 2,
          'Documentation header aligns with the centered navigation');
      }
    }
  }
}));
