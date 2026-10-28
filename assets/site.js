const base = document.body.dataset.base || '';
// Keep the heading's accessible name and layout stable throughout each cycle.
const typewriter = document.querySelector('[data-typewriter]');
if (typewriter && typeof typewriter.animate === 'function') {
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const characters = [];
  const words = typewriter.textContent.split(/(\s+)/);
  typewriter.replaceChildren();
  for (const word of words) {
    if (/^\s+$/.test(word)) {
      typewriter.append(document.createTextNode(word));
      continue;
    }
    const group = document.createElement('span');
    group.className = 'typewriter-word';
    for (const letter of word) {
      const character = document.createElement('span');
      character.className = 'typewriter-letter';
      character.textContent = letter;
      group.append(character);
      characters.push(character);
    }
    typewriter.append(group);
  }
  let timer;
  let animations = [];
  let inView = true;
  const interval = 60000;
  let nextCycle = performance.now() + 600;
  const stop = () => {
    clearTimeout(timer);
    for (const animation of animations) animation.cancel();
    animations = [];
  };
  const cycle = async () => {
    stop();
    nextCycle = performance.now() + interval;
    const fade = typewriter.animate([{ opacity: 1 }, { opacity: 0 }],
      { duration: 180, fill: 'forwards', easing: 'ease-out' });
    animations = [fade];
    try { await fade.finished; } catch { return; }
    animations = characters.map((character, index) => character.animate(
      [{ opacity: 0, transform: 'translateY(2px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 180, delay: index * 70, fill: 'both', easing: 'ease-out' }
    ));
    fade.cancel();
    timer = setTimeout(cycle, Math.max(0, nextCycle - performance.now()));
  };
  const update = () => {
    stop();
    if (!motion.matches && !document.hidden && inView) {
      // Returning to the heading must not trigger another immediate reveal.
      if (nextCycle <= performance.now()) nextCycle = performance.now() + interval;
      timer = setTimeout(cycle, nextCycle - performance.now());
    }
  };
  motion.addEventListener('change', update);
  document.addEventListener('visibilitychange', update);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      update();
    }).observe(typewriter);
  }
  update();
}
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
const faq = [...document.querySelectorAll('.faq-item')];
const filter = document.querySelector('#faq-filter');
if (filter) {
  const count = document.querySelector('#faq-count');
  const update = () => {
    const query = filter.value.trim().toLowerCase();
    let visible = 0;
    for (const item of faq) {
      item.hidden = !!query && !item.textContent.toLowerCase().includes(query);
      if (!item.hidden) visible++;
      if (query && !item.hidden) item.open = true;
    }
    count.textContent = `${visible} of ${faq.length} questions`;
  };
  filter.addEventListener('input', update);
  update();
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
