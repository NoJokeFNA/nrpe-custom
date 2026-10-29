const base = document.body.dataset.base || '';
const search = document.querySelector('#site-search');
const results = document.querySelector('#search-results');
let indexPromise;
let request = 0;
const loadIndex = () => indexPromise ||= fetch(`${base}/assets/search-index.json`).then(response => {
  if (!response.ok) throw new Error('Search index unavailable');
  return response.json();
});
const closeSearch = () => { request++; results.hidden = true; search.setAttribute('aria-expanded', 'false'); };
const element = (tag, text, className) => {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
};
search.addEventListener('input', async () => {
  const current = ++request;
  const query = search.value.trim().toLowerCase();
  if (!query) { closeSearch(); return; }
  try {
    const index = await loadIndex();
    if (current !== request) return;
    const words = query.split(/\s+/);
    const matches = index.map(page => ({page, score: words.every(word =>
      `${page.title} ${page.text}`.toLowerCase().includes(word))
        ? words.reduce((sum, word) => sum + (page.title.toLowerCase().includes(word) ? 10 : 1), 0) : 0
    })).filter(result => result.score).sort((a, b) => b.score - a.score).slice(0, 7);
    results.replaceChildren();
    for (const {page} of matches) {
      const link = element('a', '', 'search-result');
      link.href = page.url;
      const found = page.text.toLowerCase().indexOf(words[0]);
      const start = Math.max(0, found - 35);
      link.append(element('small', page.section), element('strong', page.title),
        element('p', `${start ? '…' : ''}${page.text.slice(start, start + 125)}…`));
      results.append(link);
    }
    if (!matches.length) results.append(element('p', 'No matching pages. Try a version, command or error message.', 'search-empty'));
    results.hidden = false;
    search.setAttribute('aria-expanded', 'true');
  } catch {
    if (current !== request) return;
    results.replaceChildren(element('p', 'Search is unavailable. You can still browse the documentation.', 'search-empty'));
    results.hidden = false;
    search.setAttribute('aria-expanded', 'true');
  }
});
search.addEventListener('keydown', event => {
  if (event.key === 'ArrowDown' && !results.hidden) {
    event.preventDefault(); results.querySelector('a')?.focus();
  }
  if (event.key === 'Enter' && !results.hidden) {
    const first = results.querySelector('a');
    if (first) { event.preventDefault(); first.click(); }
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    const restoreFocus = results.contains(document.activeElement);
    closeSearch();
    if (restoreFocus) search.focus();
  }
  if ((event.key === '/' || ((event.ctrlKey || event.metaKey) && event.key === 'k')) &&
      !event.target.closest('input,textarea,[contenteditable]')) {
    event.preventDefault(); search.focus();
  }
});
results.addEventListener('keydown', event => {
  const links = [...results.querySelectorAll('a')];
  const current = links.indexOf(document.activeElement);
  if (event.key === 'ArrowDown' && links.length) {
    event.preventDefault(); links[(current + 1) % links.length].focus();
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (current <= 0) search.focus(); else links[current - 1].focus();
  }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.header-tools')) closeSearch();
});
document.querySelector('.docs-toggle')?.addEventListener('click', event => {
  const toggle = event.currentTarget;
  const open = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(open));
  document.querySelector('#doc-nav').classList.toggle('mobile-open', open);
});
const faq = [...document.querySelectorAll('.faq-question')];
const filter = document.querySelector('#faq-filter');
if (filter) {
  const count = document.querySelector('#faq-count');
  const clear = document.querySelector('#faq-clear');
  const empty = document.querySelector('#faq-empty');
  const text = new Map(faq.map(item => [item, item.textContent.toLowerCase()]));
  filter.closest('.faq-tools').hidden = false;
  const highlight = (item, query) => {
    for (const mark of item.querySelectorAll('mark')) mark.replaceWith(document.createTextNode(mark.textContent));
    item.normalize();
    if (!query) return;
    const walker = document.createTreeWalker(item, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      if (!walker.currentNode.parentElement.closest('pre, code, button, .question-link')) nodes.push(walker.currentNode);
    }
    for (const node of nodes) {
      const value = node.textContent;
      const lower = value.toLowerCase();
      if (!lower.includes(query)) continue;
      const fragment = document.createDocumentFragment();
      let start = 0;
      for (let match = lower.indexOf(query); match !== -1; match = lower.indexOf(query, start)) {
        fragment.append(document.createTextNode(value.slice(start, match)));
        const mark = document.createElement('mark');
        mark.textContent = value.slice(match, match + query.length);
        fragment.append(mark);
        start = match + query.length;
      }
      fragment.append(document.createTextNode(value.slice(start)));
      node.replaceWith(fragment);
    }
  };
  const update = () => {
    const query = filter.value.trim().toLowerCase();
    let visible = 0;
    for (const item of faq) {
      item.hidden = !!query && !text.get(item).includes(query);
      if (!item.hidden) visible++;
      highlight(item, item.hidden ? '' : query);
      const id = item.querySelector('h3').id;
      document.querySelector(`.faq-index [data-question="${CSS.escape(id)}"]`).closest('li').hidden = item.hidden;
    }
    for (const group of document.querySelectorAll('.faq-group')) {
      group.hidden = [...group.querySelectorAll('.faq-question')].every(item => item.hidden);
    }
    for (const group of document.querySelectorAll('.faq-index-group')) {
      group.hidden = [...group.querySelectorAll('li')].every(item => item.hidden);
    }
    clear.hidden = !query;
    empty.hidden = visible !== 0;
    const topics = document.querySelectorAll('.faq-group').length;
    count.textContent = query ? `${visible} of ${faq.length} questions match` : `${faq.length} questions across ${topics} topics`;
    document.dispatchEvent(new Event('faq-filtered'));
  };
  filter.addEventListener('input', update);
  clear.addEventListener('click', () => { filter.value = ''; update(); filter.focus(); });
  window.addEventListener('hashchange', () => {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
    if (target?.closest('.faq-question[hidden], .faq-group[hidden]')) {
      filter.value = ''; update(); target.scrollIntoView();
    }
  });
  update();
}
// Reuse the existing page outline instead of adding another navigation rail.
if (faq.length) {
  const links = [...document.querySelectorAll('.page-toc a[href^="#"]')];
  const targets = links.map(link => document.getElementById(decodeURIComponent(link.hash.slice(1))));
  let scheduled = false;
  const track = () => {
    scheduled = false;
    const visible = targets.filter(target => target && !target.closest('[hidden]'));
    const active = visible.filter(target => target.getBoundingClientRect().top <= 160).at(-1) || visible[0];
    links.forEach((link, index) => {
      if (targets[index] === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
      link.parentElement.hidden = !!targets[index]?.closest('[hidden]');
    });
  };
  const schedule = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(track); } };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  document.addEventListener('faq-filtered', schedule);
  track();
}
function revealAnchor() {
  let id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
  const target = document.getElementById(id);
  const detail = target?.closest('details');
  if (detail) { detail.open = true; target.scrollIntoView(); }
}
window.addEventListener('hashchange', revealAnchor);
revealAnchor();
for (const block of document.querySelectorAll('.prose pre')) {
  if (block.classList.contains('mermaid') || block.querySelector('code')?.classList.contains('language-mermaid')) continue;
  const code = block.querySelector('code');
  if (!code) continue;
  const button = element('button', 'Copy', 'copy-code');
  button.type = 'button';
  button.setAttribute('aria-label', 'Copy code example');
  button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(code.textContent); button.textContent = 'Copied'; }
    catch { button.textContent = 'Select to copy'; const selection = getSelection(); const range = document.createRange(); range.selectNodeContents(code); selection.removeAllRanges(); selection.addRange(range); }
    setTimeout(() => { button.textContent = 'Copy'; }, 1800);
  });
  block.append(button);
}
