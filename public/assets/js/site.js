(() => {
  'use strict';

  const root = document.documentElement;
  const $ = (selector, context = document) => context.querySelector(selector);
  const $$ = (selector, context = document) => [...context.querySelectorAll(selector)];

  // Theme handling degrades gracefully when local storage is unavailable.
  const themeButton = $('#themeToggle');
  const themeIcon = (theme) => theme === 'dark'
    ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l-1.42 1.42m11.3-11.3 1.42-1.42"/></svg>'
    : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 15.1A8.3 8.3 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z"/></svg>';
  const setTheme = (theme) => {
    root.dataset.theme = theme;
    if (!themeButton) return;
    themeButton.innerHTML = themeIcon(theme);
    themeButton.setAttribute('aria-label', theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap');
    themeButton.title = theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap';
  };
  let savedTheme = null;
  try { savedTheme = localStorage.getItem('software-lab-theme'); } catch (_) {}
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(savedTheme === 'dark' || savedTheme === 'light' ? savedTheme : (prefersDark ? 'dark' : 'light'));
  themeButton?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('software-lab-theme', next); } catch (_) {}
  });

  // Responsive navigation.
  const menuButton = $('#menuToggle');
  const nav = $('#navLinks');
  const closeMenu = () => {
    nav?.classList.remove('is-open');
    menuButton?.setAttribute('aria-expanded', 'false');
    menuButton?.setAttribute('aria-label', 'Buka menu');
    document.body.classList.remove('menu-open');
  };
  menuButton?.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
    nav?.classList.toggle('is-open', open);
    document.body.classList.toggle('menu-open', open);
  });
  $$('#navLinks a').forEach((link) => link.addEventListener('click', closeMenu));
  window.addEventListener('resize', () => { if (window.innerWidth > 700) closeMenu(); });

  // Catalog is static JSON: no login, third-party search API, or tracking request.
  const grid = $('#softwareGrid');
  const search = $('#softwareSearch');
  const resultCount = $('#resultCount');
  const categorySelect = $('#categoryFilter');
  const platformSelect = $('#platformFilter');
  const sortSelect = $('#sortSelect');
  const pagination = $('#catalogPagination');
  const statusButtons = $$('.status-filters [data-filter]');
  const pageSize = 12;
  const validStatuses = new Set(['all', 'testing', 'planned', 'released']);
  const state = {
    query: '',
    status: 'all',
    category: 'all',
    platform: 'all',
    sort: 'name-asc',
    page: 1,
  };
  let software = [];

  const icons = {
    package: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.3 7.5 7.7 4.4 7.7-4.4M12 12v9M8 5.3l8 4.5"/></svg>',
    type: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7V4h16v3M12 4v16M8 20h8"/></svg>',
    default: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16"/><path d="M8 9h8M8 13h5"/></svg>',
  };
  const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
  const normalize = (value) => String(value ?? '').toLocaleLowerCase('id-ID')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  const statusLabel = (status) => ({
    testing: 'Dalam pengujian',
    planned: 'Direncanakan',
    released: 'Sudah dirilis',
  })[status] || 'Status belum ditetapkan';
  const statusRank = (status) => ({ released: 0, testing: 1, planned: 2 })[status] ?? 3;

  const readURLState = () => {
    const params = new URLSearchParams(window.location.search);
    state.query = params.get('q') || '';
    state.status = validStatuses.has(params.get('status')) ? (params.get('status') || 'all') : 'all';
    state.category = params.get('category') || 'all';
    state.platform = params.get('platform') || 'all';
    const sort = params.get('sort');
    state.sort = ['name-asc', 'name-desc', 'category', 'status'].includes(sort) ? sort : 'name-asc';
    state.page = Math.max(1, Number.parseInt(params.get('page') || '1', 10) || 1);
    if (search) search.value = state.query;
    if (sortSelect) sortSelect.value = state.sort;
    statusButtons.forEach((button) => {
      const selected = button.dataset.filter === state.status;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  };
  const syncURL = () => {
    const params = new URLSearchParams(window.location.search);
    const pairs = [
      ['q', state.query], ['status', state.status], ['category', state.category],
      ['platform', state.platform], ['sort', state.sort], ['page', String(state.page)],
    ];
    pairs.forEach(([key, value]) => {
      const defaultValue = key === 'status' || key === 'category' || key === 'platform' ? 'all'
        : key === 'sort' ? 'name-asc' : key === 'page' ? '1' : '';
      if (!value || value === defaultValue) params.delete(key);
      else params.set(key, value);
    });
    const queryString = params.toString();
    const next = window.location.pathname + (queryString ? '?' + queryString : '') + window.location.hash;
    window.history.replaceState(null, '', next);
  };

  const fillSelect = (select, values, defaultLabel) => {
    if (!select) return;
    const prior = select.value;
    select.innerHTML = '<option value="all">' + escapeHTML(defaultLabel) + '</option>' +
      values.map((value) => '<option value="' + escapeHTML(value) + '">' + escapeHTML(value) + '</option>').join('');
    select.value = values.includes(prior) ? prior : 'all';
  };

  const filteredRows = () => {
    const query = normalize(state.query);
    const rows = software.filter((app) => {
      if (state.status !== 'all' && app.status !== state.status) return false;
      if (state.category !== 'all' && app.category !== state.category) return false;
      if (state.platform !== 'all' && !(app.platforms || []).includes(state.platform)) return false;
      if (!query) return true;
      const searchable = [
        app.name, app.summary, app.description, app.category, app.status,
        ...(app.tags || []), ...(app.platforms || []), ...(app.keywords || []),
        ...(app.features || []),
      ];
      return searchable.some((value) => normalize(value).includes(query));
    });
    rows.sort((a, b) => {
      if (state.sort === 'name-desc') return String(b.name).localeCompare(String(a.name), 'id');
      if (state.sort === 'category') {
        return String(a.category).localeCompare(String(b.category), 'id') || String(a.name).localeCompare(String(b.name), 'id');
      }
      if (state.sort === 'status') {
        return statusRank(a.status) - statusRank(b.status) || String(a.name).localeCompare(String(b.name), 'id');
      }
      return String(a.name).localeCompare(String(b.name), 'id');
    });
    return rows;
  };

  const emptyState = (query) => {
    const webSearch = query
      ? '<p class="web-search-note">Tidak menemukan aplikasi lokal yang cocok. Pencarian web dilakukan hanya saat kamu menekan tautan ini.</p><a class="btn btn-secondary web-search-link" target="_blank" rel="noopener noreferrer" href="https://www.google.com/search?q=' + encodeURIComponent(query + ' software Linux') + '">Cari di web ↗</a>'
      : '<p>Belum ada aplikasi yang cocok dengan filter saat ini.</p>';
    return '<div class="empty-state"><strong>Tidak ada software yang cocok.</strong><p>Coba kata kunci atau ubah filter.</p>' + webSearch + '</div>';
  };

  const renderPagination = (totalRows, totalPages) => {
    if (!pagination) return;
    if (totalPages <= 1) {
      pagination.hidden = true;
      pagination.innerHTML = '';
      return;
    }
    pagination.hidden = false;
    pagination.innerHTML =
      '<button class="btn btn-secondary pagination-button" type="button" data-page="prev"' + (state.page <= 1 ? ' disabled' : '') + '>← Sebelumnya</button>' +
      '<span class="pagination-info">Halaman <strong>' + state.page + '</strong> dari <strong>' + totalPages + '</strong> · ' + totalRows + ' hasil</span>' +
      '<button class="btn btn-secondary pagination-button" type="button" data-page="next"' + (state.page >= totalPages ? ' disabled' : '') + '>Berikutnya →</button>';
    pagination.querySelector('[data-page="prev"]')?.addEventListener('click', () => {
      state.page = Math.max(1, state.page - 1);
      render();
    });
    pagination.querySelector('[data-page="next"]')?.addEventListener('click', () => {
      state.page = Math.min(totalPages, state.page + 1);
      render();
    });
  };

  const render = () => {
    if (!grid) return;
    const rows = filteredRows();
    const total = rows.length;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    state.page = Math.min(state.page, pages);
    const shown = rows.slice((state.page - 1) * pageSize, state.page * pageSize);
    if (resultCount) {
      resultCount.textContent = total
        ? 'Menampilkan ' + ((state.page - 1) * pageSize + 1) + '–' + Math.min(state.page * pageSize, total) + ' dari ' + total + ' hasil (' + software.length + ' software terdaftar)'
        : '0 hasil dari ' + software.length + ' software terdaftar';
    }
    if (!total) {
      grid.innerHTML = emptyState(state.query);
    } else {
      grid.innerHTML = shown.map((app, index) => {
        const status = ['testing', 'planned', 'released'].includes(app.status) ? app.status : 'planned';
        const tags = (app.tags || []).slice(0, 6).map((tag) => '<span class="tag">' + escapeHTML(tag) + '</span>').join('');
        const preview = escapeHTML(app.previewImage || '/assets/images/software-preview-placeholder.svg');
        const iconImage = escapeHTML(app.iconImage || '');
        const previewAlt = escapeHTML(app.previewAlt || ('Ilustrasi konsep antarmuka ' + app.name));
        const iconMarkup = iconImage
          ? '<img src="' + iconImage + '" alt="" width="64" height="64" loading="lazy" decoding="async">'
          : (icons[app.icon] || icons.default);
        const number = (state.page - 1) * pageSize + index + 1;
        const sourceNote = app.sourceUrl ? '<a class="card-link card-source-link" href="' + escapeHTML(app.sourceUrl) + '" target="_blank" rel="noopener noreferrer">Kode sumber ↗</a>' : '';
        return '<article class="software-card">' +
          '<div class="software-card-top"><span class="software-index">' + String(number).padStart(3, '0') + ' / LAB</span><span class="status-badge ' + status + '">' + escapeHTML(statusLabel(status)) + '</span></div>' +
          '<a class="software-preview" href="' + escapeHTML(app.detailUrl || '#software') + '" aria-label="Buka detail ' + escapeHTML(app.name) + '"><img src="' + preview + '" alt="' + previewAlt + '" width="960" height="600" loading="lazy" decoding="async"></a>' +
          '<div class="software-card-content"><div class="software-card-heading"><span class="app-icon">' + iconMarkup + '</span></div>' +
          '<div class="software-card-category">' + escapeHTML(app.category || 'Software') + '</div>' +
          '<h3><a href="' + escapeHTML(app.detailUrl || '#software') + '">' + escapeHTML(app.name) + '</a></h3>' +
          '<p class="summary">' + escapeHTML(app.summary) + '</p><div class="tag-list">' + tags + '</div>' +
          '<div class="software-card-platforms">' + escapeHTML((app.platforms || ['Linux']).join(' · ')) + '</div>' +
          '<div class="card-bottom"><a class="card-link" href="' + escapeHTML(app.detailUrl || '#software') + '">Detail proyek ↗</a>' + sourceNote + '</div></div></article>';
      }).join('');
    }
    renderPagination(total, pages);
    syncURL();
  };

  statusButtons.forEach((button) => button.addEventListener('click', () => {
    state.status = button.dataset.filter || 'all';
    state.page = 1;
    statusButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    render();
  }));
  search?.addEventListener('input', () => {
    state.query = search.value;
    state.page = 1;
    render();
  });
  categorySelect?.addEventListener('change', () => { state.category = categorySelect.value; state.page = 1; render(); });
  platformSelect?.addEventListener('change', () => { state.platform = platformSelect.value; state.page = 1; render(); });
  sortSelect?.addEventListener('change', () => { state.sort = sortSelect.value; state.page = 1; render(); });
  $('#resetFilters')?.addEventListener('click', () => {
    state.query = '';
    state.status = 'all';
    state.category = 'all';
    state.platform = 'all';
    state.sort = 'name-asc';
    state.page = 1;
    if (search) search.value = '';
    if (categorySelect) categorySelect.value = 'all';
    if (platformSelect) platformSelect.value = 'all';
    if (sortSelect) sortSelect.value = state.sort;
    statusButtons.forEach((button) => {
      const selected = button.dataset.filter === 'all';
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    render();
  });

  readURLState();
  fetch('/data/software.json', { headers: { Accept: 'application/json' } })
    .then((response) => {
      if (!response.ok) throw new Error('Katalog tidak tersedia');
      return response.json();
    })
    .then((payload) => {
      if (!payload || !Array.isArray(payload.software)) throw new Error('Format katalog tidak valid');
      software = payload.software;
      fillSelect(categorySelect, [...new Set(software.map((app) => app.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'id')), 'Semua kategori');
      fillSelect(platformSelect, [...new Set(software.flatMap((app) => app.platforms || []))].sort((a, b) => a.localeCompare(b, 'id')), 'Semua platform');
      // Restore filter choices from shareable URL parameters after options exist.
      const params = new URLSearchParams(window.location.search);
      if ([...categorySelect.options].some((option) => option.value === state.category)) categorySelect.value = state.category;
      else state.category = 'all';
      if ([...platformSelect.options].some((option) => option.value === state.platform)) platformSelect.value = state.platform;
      else state.platform = 'all';
      if (sortSelect) sortSelect.value = state.sort;
      render();
    })
    .catch(() => {
      if (grid) grid.innerHTML = '<div class="empty-state"><strong>Katalog belum dapat dimuat.</strong><p>Periksa koneksi dan coba muat ulang halaman.</p><a class="btn btn-secondary" href="/">Muat ulang halaman ↻</a></div>';
      if (resultCount) resultCount.textContent = 'Katalog tidak tersedia';
      if (pagination) pagination.hidden = true;
    });

  const year = $('#year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
