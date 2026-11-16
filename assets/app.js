(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const $ = id => document.getElementById(id);
  const chapters = [...document.querySelectorAll('.chapter')];
  const byId = new Map(chapters.map(chapter => [chapter.id, chapter]));
  const navLinks = [...document.querySelectorAll('[data-nav]')];
  const search = $('search');
  const searchPanel = $('searchResults');
  const normalize = value => value.toLocaleLowerCase('ru').replaceAll('ё', 'е').replace(/[\s\u00a0\u202f]+/g, ' ').trim();
  const index = chapters.map(chapter => {
    const title = chapter.querySelector('h1').textContent;
    const body = chapter.querySelector('.prose').innerText.replace(/[\s\u00a0\u202f]+/g, ' ').trim();
    return { chapter, title, body, normalized: normalize(title + ' ' + chapter.dataset.keywords + ' ' + body), normalizedTitle: normalize(title) };
  });
  let current = chapters[0];
  let toastTimer;
  let searchTimer;
  const mobile = window.matchMedia('(max-width: 900px)');

  function drawer(open) {
    document.body.classList.toggle('drawer-open', open);
    $('menuToggle').setAttribute('aria-expanded', String(open));
    $('menuToggle').setAttribute('aria-label', open ? 'Закрыть оглавление' : 'Открыть оглавление');
    $('drawerBackdrop').hidden = !open;
    // Prevent hidden mobile links from entering the keyboard focus order.
    $('sidebar').inert = mobile.matches && !open;
    if (open) search.focus();
  }

  function route(focus = false) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { id = ''; }
    const target = document.getElementById(id);
    current = byId.get(id) || target?.closest('.chapter') || chapters[0];
    for (const chapter of chapters) chapter.hidden = chapter !== current;
    searchPanel.hidden = true;
    search.value = '';
    for (const link of navLinks) {
      if (link.dataset.nav === current.id) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    $('breadcrumb').textContent = current.dataset.group;
    document.title = current.querySelector('h1').textContent + ' — инструкция ПарДозора';
    const heading = target?.matches('h2,h3') ? target : current.querySelector('h1');
    if (focus || id) {
      requestAnimationFrame(() => {
        if (focus) heading.focus({ preventScroll: true });
        heading.scrollIntoView({ behavior: 'instant', block: 'start' });
      });
    }
    drawer(false);
  }

  function snippet(item, words) {
    const body = normalize(item.body);
    let position = body.indexOf(words[0]);
    if (position < 0) position = 0;
    const start = Math.max(0, position - 65);
    return (start ? '…' : '') + item.body.slice(start, start + 230).trim() + (start + 230 < item.body.length ? '…' : '');
  }

  function highlighted(text, words) {
    // Build text nodes, never interpolate the query into HTML or a RegExp.
    const fragment = document.createDocumentFragment();
    const normalized = normalize(text);
    const intervals = [];
    for (const word of words) {
      let position = 0;
      while ((position = normalized.indexOf(word, position)) >= 0) {
        intervals.push([position, position + word.length]);
        position += Math.max(1, word.length);
      }
    }
    intervals.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const interval of intervals) {
      const last = merged.at(-1);
      if (last && interval[0] <= last[1]) last[1] = Math.max(last[1], interval[1]);
      else merged.push([...interval]);
    }
    let position = 0;
    for (const [start, end] of merged) {
      fragment.append(document.createTextNode(text.slice(position, start)));
      const mark = document.createElement('mark');
      mark.textContent = text.slice(start, end);
      fragment.append(mark);
      position = end;
    }
    fragment.append(document.createTextNode(text.slice(position)));
    return fragment;
  }

  function runSearch(moveFocus = false) {
    clearTimeout(searchTimer);
    const query = normalize(search.value).slice(0, 150);
    if (!query) { route(false); return; }
    const words = query.split(' ').filter(Boolean).slice(0, 12);
    const results = index.filter(item => words.every(word => item.normalized.includes(word)));
    results.sort((a, b) => words.filter(word => b.normalizedTitle.includes(word)).length - words.filter(word => a.normalizedTitle.includes(word)).length);
    for (const chapter of chapters) chapter.hidden = true;
    searchPanel.hidden = false;
    $('breadcrumb').textContent = 'Поиск';
    $('searchSummary').textContent = `Запрос «${search.value.trim().slice(0, 150)}» · найдено глав: ${results.length}`;
    $('searchList').replaceChildren();
    for (const item of results) {
      const link = document.createElement('a');
      link.className = 'search-result';
      link.href = '#' + item.chapter.id;
      const group = document.createElement('small');
      group.textContent = item.chapter.dataset.group;
      const title = document.createElement('h2');
      title.append(highlighted(item.title, words));
      const excerpt = document.createElement('p');
      excerpt.append(highlighted(snippet(item, words), words));
      link.append(group, title, excerpt);
      $('searchList').append(link);
    }
    if (!results.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-search';
      empty.textContent = 'Попробуйте другое слово или его часть: например, «опорн», «восстановление», «ШИМ», «пароль» или «CSV».';
      $('searchList').append(empty);
    }
    document.title = 'Поиск — инструкция ПарДозора';
    if (moveFocus && mobile.matches) {
      drawer(false);
      $('searchTitle').setAttribute('tabindex', '-1');
      $('searchTitle').focus({ preventScroll: true });
      $('searchTitle').scrollIntoView({ behavior: 'instant', block: 'start' });
    }
  }

  function toast(message) {
    clearTimeout(toastTimer);
    $('toast').textContent = message;
    toastTimer = setTimeout(() => { $('toast').textContent = ''; }, 4000);
  }

  async function copyLink() {
    const url = new URL(location.href);
    if (!url.hash || !searchPanel.hidden) url.hash = current.id;
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url.href);
      else {
        const field = document.createElement('textarea');
        field.value = url.href;
        field.style.position = 'fixed';
        field.style.top = '-1000px';
        document.body.append(field);
        field.select();
        const copied = document.execCommand('copy');
        field.remove();
        if (!copied) throw new Error('Clipboard unavailable');
      }
      toast('Ссылка на раздел скопирована');
    } catch { toast('Не удалось скопировать. Скопируйте адрес из строки браузера.'); }
  }

  function print(all) {
    if (!all && !searchPanel.hidden) route(false);
    document.body.dataset.print = all ? 'all' : 'chapter';
    window.print();
  }

  $('menuToggle').addEventListener('click', () => drawer(!document.body.classList.contains('drawer-open')));
  $('drawerBackdrop').addEventListener('click', () => { drawer(false); $('menuToggle').focus(); });
  $('searchForm').addEventListener('submit', event => { event.preventDefault(); runSearch(true); });
  search.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => runSearch(false), 120); });
  search.addEventListener('search', () => runSearch(false));
  $('copyLink').addEventListener('click', copyLink);
  $('printChapter').addEventListener('click', () => print(false));
  $('printAll').addEventListener('click', () => print(true));
  window.addEventListener('afterprint', () => { delete document.body.dataset.print; });
  window.addEventListener('hashchange', () => route(true));
  mobile.addEventListener('change', () => drawer(false));
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || link.classList.contains('skip-link')) return;
    if (link.hash === location.hash) {
      event.preventDefault();
      route(true); // Also restore a chapter when a search result has the same hash.
    }
  });
  document.addEventListener('keydown', event => {
    const typing = event.target.matches('input,textarea,select,[contenteditable=true]');
    if ((event.key === '/' && !typing) || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k')) {
      event.preventDefault();
      if (mobile.matches) drawer(true);
      search.focus();
    }
    if (event.key === 'Escape') {
      if (search.value) { search.value = ''; route(false); }
      drawer(false);
      if (mobile.matches) $('menuToggle').focus();
    }
    if (event.key === 'Tab' && mobile.matches && document.body.classList.contains('drawer-open')) {
      const focusable = [...$('sidebar').querySelectorAll('a,input,button')].filter(node => !node.disabled);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  for (const table of document.querySelectorAll('.table-wrap')) {
    table.setAttribute('tabindex', '0');
    table.setAttribute('role', 'region');
    table.setAttribute('aria-label', 'Таблица. На небольшом экране можно прокрутить по горизонтали.');
  }
  route();
})();
