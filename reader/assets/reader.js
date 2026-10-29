(() => {
  const body = document.body;
  const theme = document.querySelector('#theme');
  const share = document.querySelector('#share');
  const narrowScreen = matchMedia('(max-width: 720px)');
  const panels = [...document.querySelectorAll('.contents, .reading-options')];
  function updatePanels() { panels.forEach(panel => { panel.open = !narrowScreen.matches; }); }
  updatePanels();
  narrowScreen.addEventListener('change', updatePanels);
  document.querySelector('aside').addEventListener('click', event => {
    if (narrowScreen.matches && event.target.closest('a[href^="#"]')) {
      panels.forEach(panel => { panel.open = false; });
    }
  });
  let size = 19;
  try {
    size = Math.max(16, Math.min(26, Number(localStorage.getItem('mvl-text-size')) || 19));
    body.classList.toggle('light', localStorage.getItem('mvl-theme') === 'light');
  } catch {}
  function applySettings() {
    body.style.setProperty('--size', `${size}px`);
    theme.textContent = body.classList.contains('light') ? 'Тёмная тема' : 'Светлая тема';
    document.querySelector('#smaller').disabled = size <= 16;
    document.querySelector('#larger').disabled = size >= 26;
    try {
      localStorage.setItem('mvl-text-size', String(size));
      localStorage.setItem('mvl-theme', body.classList.contains('light') ? 'light' : 'dark');
    } catch {}
  }
  theme.addEventListener('click', () => { body.classList.toggle('light'); applySettings(); });
  document.querySelector('#smaller').addEventListener('click', () => { size = Math.max(16, size - 1); applySettings(); });
  document.querySelector('#larger').addEventListener('click', () => { size = Math.min(26, size + 1); applySettings(); });
  applySettings();
  share?.addEventListener('click', async () => {
    const payload = { title: document.title, text: document.querySelector('meta[name="description"]')?.content || '', url: location.href };
    try {
      if (navigator.share) {
        await navigator.share(payload);
        return;
      }
      await navigator.clipboard.writeText(location.href);
      const original = share.textContent;
      share.textContent = 'Ссылка скопирована';
      setTimeout(() => { share.textContent = original; }, 1800);
    } catch (error) {
      if (error?.name !== 'AbortError') share.textContent = 'Скопируйте адрес страницы';
    }
  });
  const viewer = document.querySelector('#image-viewer');
  const viewerImage = document.querySelector('#viewer-image');
  const viewerCaption = document.querySelector('#viewer-caption');
  const viewerClose = document.querySelector('.viewer-close');
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-lightbox]');
    if (!link || !viewer) return;
    event.preventDefault();
    viewerImage.src = link.href;
    viewerImage.alt = link.dataset.caption || link.querySelector('img')?.alt || '';
    viewerCaption.textContent = link.dataset.caption || viewerImage.alt;
    viewer.showModal();
  });
  viewerClose?.addEventListener('click', () => viewer.close());
  viewer?.addEventListener('click', event => {
    if (event.target === viewer) viewer.close();
  });
  viewer?.addEventListener('close', () => {
    viewerImage.removeAttribute('src');
  });
  const paragraphs = [...document.querySelectorAll('article p, article li, article h2, article h3')];
  paragraphs.forEach((element, i) => { if (!element.id) element.id = `paragraph-${i}`; });
  const search = document.querySelector('#search');
  const results = document.querySelector('#results');
  const status = document.querySelector('#search-status');
  search.addEventListener('input', () => {
    const term = search.value.trim().toLocaleLowerCase('ru');
    results.replaceChildren();
    if (!term) { status.textContent = ''; return; }
    const matches = paragraphs.filter(p => p.textContent.toLocaleLowerCase('ru').includes(term));
    status.textContent = matches.length ? `Совпадений: ${matches.length}` : 'Совпадений нет';
    matches.slice(0, 30).forEach(p => {
      const link = document.createElement('a');
      link.href = `#${p.id}`;
      link.textContent = p.textContent.trim().slice(0, 130) + (p.textContent.length > 130 ? '…' : '');
      results.append(link);
    });
  });
  const progress = document.querySelector('.progress');
  function updateProgress() {
    const distance = document.documentElement.scrollHeight - innerHeight;
    progress.style.width = `${distance > 0 ? scrollY / distance * 100 : 0}%`;
  }
  addEventListener('scroll', updateProgress, { passive: true });
  addEventListener('resize', updateProgress);
  updateProgress();
})();
