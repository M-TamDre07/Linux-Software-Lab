(() => {
'use strict';

const root = document.documentElement;
const $ = (selector, context = document) => context.querySelector(selector);
const $$ = (selector, context = document) => [...context.querySelectorAll(selector)];

const themeButton = $('#themeToggle');
const themeIcon = theme => theme === 'dark'
  ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>'
  : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 15.1A8.3 8.3 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z"/></svg>';

const setTheme = theme => {
  root.dataset.theme = theme;
  if (!themeButton) return;
  themeButton.innerHTML = themeIcon(theme);
  themeButton.setAttribute('aria-label', theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap');
  themeButton.title = theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap';
};

let savedTheme = null;
try { savedTheme = localStorage.getItem('software-lab-theme'); } catch (_) {}
const preferredTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
setTheme(savedTheme === 'dark' || savedTheme === 'light' ? savedTheme : preferredTheme);

themeButton?.addEventListener('click', () => {
  const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  setTheme(nextTheme);
  try { localStorage.setItem('software-lab-theme', nextTheme); } catch (_) {}
});

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
$$('#navLinks a').forEach(link => link.addEventListener('click', closeMenu));
window.addEventListener('resize', () => { if (window.innerWidth > 700) closeMenu(); });

const grid = $('#softwareGrid');
const searchInput = $('#softwareSearch');
const resultCount = $('#resultCount');
const statusButtons = $$('.filter-btn[data-filter]');
const categorySelect = $('#categoryFilter');
const platformSelect = $('#platformFilter');
const sortSelect = $('#sortFilter');
const loadMoreButton = $('#loadMore');
const paginationSummary = $('#paginationSummary');
const clearButton = $('#clearFilters');
let pageSize = 12;
const STATUS_LABELS = { released: 'Sudah dirilis', testing: 'Dalam pengujian', planned: 'Direncanakan', archived: 'Arsip' };
const STATUS_ORDER = { released: 0, testing: 1, planned: 2, archived: 3 };
const ICONS = {
  package: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.3 7.5 7.7 4.4 7.7-4.4M12 12v9M8 5.3l8 4.5"/></svg>',
  type: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7V4h16v3M12 4v16M8 20h8"/></svg>',
  default: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h5"/></svg>'
};

let software = [];
let activeStatus = 'all';
let activeCategory = 'all';
let activePlatform = 'all';
let query = '';
let sortMode = 'relevance';
let visibleLimit = pageSize;
let catalogLoaded = false;

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

const normalise = value => String(value ?? '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLocaleLowerCase('id-ID')
  .trim();

const statusLabel = status => STATUS_LABELS[status] || 'Status belum ditetapkan';

const safeInternalPath = value => {
  const path = String(value || '');
  if (!path.startsWith('/software/') || path.startsWith('//') || path.includes('..') || /[<>"'\s]/.test(path)) return '';
  return path;
};

const safeAssetPath = value => {
  const path = String(value || '');
  if (!path.startsWith('/assets/images/') || path.startsWith('//') || path.includes('..') || /[<>"'\s]/.test(path)) return '';
  return path;
};

const safeExternalURL = value => {
  const url = String(value || '');
  if (!url.startsWith('https://') || /[\s<>"']/.test(url)) return '';
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' ? url : '';
  } catch (_) {
    return '';
  }
};

const makeSearchIndex = app => {
  const values = [
    app.name, app.summary, app.description, app.category, app.status, app.version,
    app.type, ...(app.tags || []), ...(app.keywords || []), ...(app.features || []),
    ...(app.platforms || [])
  ];
  app._searchText = normalise(values.join(' '));
  app._nameSearch = normalise(app.name);
  app._summarySearch = normalise(app.summary);
  app._categorySearch = normalise(app.category);
  app._tagSearch = normalise([...(app.tags || []), ...(app.keywords || [])].join(' '));
  app._updatedTime = Date.parse(app.updatedAt || '') || 0;
  return app;
};

const fillOptions = (select, values, placeholder) => {
  if (!select) return;
  const previous = select.value || 'all';
  const options = ['<option value="all">' + escapeHTML(placeholder) + '</option>'];
  values.forEach(value => options.push('<option value="' + escapeHTML(value) + '">' + escapeHTML(value) + '</option>'));
  select.innerHTML = options.join('');
  select.value = values.includes(previous) ? previous : 'all';
};

const currentURLState = () => {
  const url = new URL(window.location.href);
  const params = url.searchParams;
  return {
    q: params.get('q') || '',
    status: params.get('status') || 'all',
    category: params.get('category') || 'all',
    platform: params.get('platform') || 'all',
    sort: params.get('sort') || 'relevance'
  };
};

const applyURLState = () => {
  const state = currentURLState();
  query = state.q;
  if (searchInput) searchInput.value = query;
  activeStatus = ['all', 'released', 'testing', 'planned', 'archived'].includes(state.status) ? state.status : 'all';
  activeCategory = [...categorySelect?.options || []].some(option => option.value === state.category) ? state.category : 'all';
  activePlatform = [...platformSelect?.options || []].some(option => option.value === state.platform) ? state.platform : 'all';
  sortMode = ['relevance', 'name', 'name-desc', 'updated', 'status'].includes(state.sort) ? state.sort : 'relevance';
  if (categorySelect) categorySelect.value = activeCategory;
  if (platformSelect) platformSelect.value = activePlatform;
  if (sortSelect) sortSelect.value = sortMode;
  statusButtons.forEach(button => {
    const selected = button.dataset.filter === activeStatus;
    button.classList.toggle('is-active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  visibleLimit = pageSize;
};

const updateURL = () => {
  const url = new URL(window.location.href);
  const pairs = [
    ['q', query], ['status', activeStatus], ['category', activeCategory],
    ['platform', activePlatform], ['sort', sortMode]
  ];
  pairs.forEach(([key, value]) => {
    if (value && value !== 'all' && value !== 'relevance') url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  });
  window.history.replaceState(null, '', url.pathname + (url.search ? url.search : '') + url.hash);
};

const getFilteredRows = () => {
  const tokens = normalise(query).split(/\s+/).filter(Boolean);
  const rows = software.filter(app => {
    if (activeStatus !== 'all' && app.status !== activeStatus) return false;
    if (activeCategory !== 'all' && app.category !== activeCategory) return false;
    if (activePlatform !== 'all' && !(app.platforms || []).includes(activePlatform)) return false;
    return tokens.every(token => app._searchText.includes(token));
  });

  rows.sort((a, b) => {
    if (sortMode === 'name') return a._nameSearch.localeCompare(b._nameSearch, 'id');
    if (sortMode === 'name-desc') return b._nameSearch.localeCompare(a._nameSearch, 'id');
    if (sortMode === 'updated') return b._updatedTime - a._updatedTime || a._nameSearch.localeCompare(b._nameSearch, 'id');
    if (sortMode === 'status') return (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9) || a._nameSearch.localeCompare(b._nameSearch, 'id');
    const rank = app => {
      if (!tokens.length) return 0;
      let score = 0;
      if (app._nameSearch.includes(normalise(query))) score += 100;
      tokens.forEach(token => {
        if (app._nameSearch.includes(token)) score += 20;
        if (app._summarySearch.includes(token)) score += 5;
        if (app._categorySearch.includes(token)) score += 4;
        if (app._tagSearch.includes(token)) score += 2;
      });
      return score;
    };
    return rank(b) - rank(a) || a._nameSearch.localeCompare(b._nameSearch, 'id');
  });
  return rows;
};

const cardMarkup = (app, index) => {
  const status = ['released', 'testing', 'planned', 'archived'].includes(app.status) ? app.status : 'planned';
  const detail = safeInternalPath(app.detailUrl);
  const source = safeExternalURL(app.sourceUrl);
  const release = safeExternalURL(app.releaseUrl);
  const preview = safeAssetPath(app.previewImage) || '/assets/images/linux-software-lab.svg';
  const iconPath = safeAssetPath(app.iconImage);
  const iconMarkup = iconPath
    ? '<img src="' + escapeHTML(iconPath) + '" alt="" width="64" height="64" loading="lazy" decoding="async">'
    : (ICONS[app.icon] || ICONS.default);
  const tags = (app.tags || []).slice(0, 5)
    .map(tag => '<span class="tag">' + escapeHTML(tag) + '</span>').join('');
  const projectLink = detail
    ? '<a class="card-link" href="' + escapeHTML(detail) + '">Detail proyek ↗</a>'
    : '<span class="card-link is-muted">Detail segera hadir</span>';
  const externalLinks = [
    source ? '<a class="card-secondary-link" href="' + escapeHTML(source) + '" target="_blank" rel="noopener noreferrer">Kode sumber ↗</a>' : '',
    release ? '<a class="card-secondary-link" href="' + escapeHTML(release) + '" target="_blank" rel="noopener noreferrer">Unduh ↗</a>' : ''
  ].filter(Boolean).join('');
  return '<article class="software-card" data-software-id="' + escapeHTML(app.id) + '">' +
    '<div class="software-card-top"><span class="software-index">' + String(index + 1).padStart(2, '0') + ' / LAB</span>' +
    '<span class="status-badge ' + status + '">' + escapeHTML(statusLabel(status)) + '</span></div>' +
    '<a class="software-preview" href="' + escapeHTML(detail || '#software') + '" aria-label="Buka detail ' + escapeHTML(app.name) + '">' +
    '<img src="' + escapeHTML(preview) + '" alt="' + escapeHTML(app.previewAlt || ('Ilustrasi konsep ' + app.name)) + '" width="960" height="600" loading="lazy" decoding="async"></a>' +
    '<div class="software-card-content"><div class="software-card-heading"><span class="app-icon">' + iconMarkup + '</span>' +
    '<span class="software-category">' + escapeHTML(app.category || 'Software') + '</span></div>' +
    '<h3>' + escapeHTML(app.name) + '</h3><p class="summary">' + escapeHTML(app.summary) + '</p>' +
    '<div class="tag-list">' + tags + '</div>' +
    '<div class="card-bottom"><small>' + escapeHTML((app.platforms || ['Linux']).join(' · ')) + '</small>' + projectLink + '</div>' +
    (externalLinks ? '<div class="card-extra-links">' + externalLinks + '</div>' : '') +
    '</div></article>';
};

const render = () => {
  if (!grid) return;
  if (!catalogLoaded) return;
  const rows = getFilteredRows();
  const shown = rows.slice(0, visibleLimit);
  grid.innerHTML = shown.length
    ? shown.map((app, index) => cardMarkup(app, index)).join('')
    : '<div class="empty-state"><strong>Tidak ada software yang cocok.</strong><span>Periksa ejaan atau reset kategori, platform, dan status filter.</span></div>';

  if (resultCount) {
    resultCount.textContent = rows.length === 0
      ? 'Tidak ada hasil · ' + software.length + ' proyek di katalog'
      : 'Menampilkan ' + shown.length + ' dari ' + rows.length + ' hasil · ' + software.length + ' proyek di katalog';
  }
  if (paginationSummary) {
    paginationSummary.textContent = rows.length > pageSize ? 'Halaman katalog dimuat bertahap agar tetap ringan.' : 'Seluruh hasil yang cocok sudah ditampilkan.';
  }
  if (loadMoreButton) {
    loadMoreButton.hidden = shown.length >= rows.length;
    loadMoreButton.textContent = 'Muat ' + Math.min(pageSize, rows.length - shown.length) + ' berikutnya';
  }
  $$('.software-preview img', grid).forEach(image => {
    image.addEventListener('error', () => {
      if (image.dataset.fallbackUsed) return;
      image.dataset.fallbackUsed = 'true';
      image.src = '/assets/images/linux-software-lab.svg';
    }, { once: true });
  });
};

const refresh = (writeURL = true) => {
  render();
  if (writeURL) updateURL();
};

const resetFilters = () => {
  query = '';
  activeStatus = 'all';
  activeCategory = 'all';
  activePlatform = 'all';
  sortMode = 'relevance';
  visibleLimit = pageSize;
  if (searchInput) searchInput.value = '';
  if (categorySelect) categorySelect.value = 'all';
  if (platformSelect) platformSelect.value = 'all';
  if (sortSelect) sortSelect.value = 'relevance';
  statusButtons.forEach(button => {
    const selected = button.dataset.filter === 'all';
    button.classList.toggle('is-active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  refresh();
};

statusButtons.forEach(button => button.addEventListener('click', () => {
  activeStatus = button.dataset.filter || 'all';
  visibleLimit = pageSize;
  statusButtons.forEach(item => {
    const selected = item === button;
    item.classList.toggle('is-active', selected);
    item.setAttribute('aria-pressed', String(selected));
  });
  refresh();
}));
searchInput?.addEventListener('input', () => {
  query = searchInput.value;
  visibleLimit = pageSize;
  refresh();
});
categorySelect?.addEventListener('change', () => {
  activeCategory = categorySelect.value;
  visibleLimit = pageSize;
  refresh();
});
platformSelect?.addEventListener('change', () => {
  activePlatform = platformSelect.value;
  visibleLimit = pageSize;
  refresh();
});
sortSelect?.addEventListener('change', () => {
  sortMode = sortSelect.value;
  visibleLimit = pageSize;
  refresh();
});
clearButton?.addEventListener('click', () => {
  resetFilters();
  searchInput?.focus();
});
loadMoreButton?.addEventListener('click', () => {
  visibleLimit += pageSize;
  refresh(false);
});

document.addEventListener('keydown', event => {
  const target = event.target;
  const typing = target instanceof HTMLElement && (
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable
  );
  if ((event.key === '/' && !typing) || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k')) {
    event.preventDefault();
    searchInput?.focus();
    searchInput?.select();
  }
  if (event.key === 'Escape' && target === searchInput && searchInput.value) {
    searchInput.value = '';
    query = '';
    visibleLimit = pageSize;
    refresh();
  }
});

window.addEventListener('popstate', () => {
  if (!catalogLoaded) return;
  applyURLState();
  refresh(false);
});

const updateCatalogOverview = () => {
  const values = [
    ['catalogTotal', software.length],
    ['catalogReleased', software.filter(app => app.status === 'released').length],
    ['catalogInDevelopment', software.filter(app => app.status === 'testing' || app.status === 'planned').length],
    ['catalogPlatforms', new Set(software.flatMap(app => app.platforms || [])).size]
  ];
  values.forEach(([id, value]) => {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value);
  });
};

const fillCatalogControls = () => {
  const categories = [...new Set(software.map(app => app.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'id'));
  const platforms = [...new Set(software.flatMap(app => app.platforms || []).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'id'));
  fillOptions(categorySelect, categories, 'Semua kategori');
  fillOptions(platformSelect, platforms, 'Semua platform');
};

const year = $('#year');
if (year) year.textContent = String(new Date().getFullYear());

const fetchStaticCatalog = async () => {
  const response = await fetch('/data/software.json', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error('Katalog statis tidak dapat dimuat (HTTP ' + response.status + ').');
  return response.json();
};

const fetchSupabaseCatalog = async () => {
  const config = window.LSL_SUPABASE_CONFIG;
  if (!config || !config.url || !config.publishableKey) throw new Error('Supabase browser config is missing.');
  const endpoint = new URL('/rest/v1/software_catalog', config.url);
  endpoint.search = new URLSearchParams({
    select: 'id,slug,name,version,summary,description,category,status,type,platforms,tags,keywords,features,detail_url,source_url,release_url,icon,icon_image,preview_image,preview_alt,updated_at,sort_order',
    published: 'eq.true',
    order: 'sort_order.asc,name.asc'
  }).toString();
  const response = await fetch(endpoint.toString(), {
    headers: {
      apikey: config.publishableKey,
      Authorization: 'Bearer ' + config.publishableKey,
      Accept: 'application/json'
    }
  });
  if (!response.ok) throw new Error('Supabase catalogue request failed (HTTP ' + response.status + ').');
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('Supabase catalogue is empty or malformed.');
  const mapped = rows.map(row => ({
    id: row.id, slug: row.slug, name: row.name, version: row.version,
    summary: row.summary, description: row.description, category: row.category,
    status: row.status, type: row.type,
    platforms: Array.isArray(row.platforms) ? row.platforms : [],
    tags: Array.isArray(row.tags) ? row.tags : [],
    keywords: Array.isArray(row.keywords) ? row.keywords : [],
    features: Array.isArray(row.features) ? row.features : [],
    detailUrl: row.detail_url, sourceUrl: row.source_url, releaseUrl: row.release_url,
    icon: row.icon, iconImage: row.icon_image, previewImage: row.preview_image,
    previewAlt: row.preview_alt,
    updatedAt: typeof row.updated_at === 'string' ? row.updated_at.slice(0, 10) : ''
  }));
  if (mapped.some(app => !app.id || !app.name || !app.detailUrl || !app.iconImage || !app.previewImage)) {
    throw new Error('Supabase catalogue contains incomplete records.');
  }
  const latestDate = mapped.map(app => app.updatedAt).filter(Boolean).sort().pop() || '';
  return {
    schemaVersion: 2,
    catalog: {
      name: 'Linux Software Lab',
      description: 'Katalog software desktop independen untuk Debian dan keluarga Linux.',
      searchMode: 'client-side',
      pageSize: pageSize,
      updatedAt: latestDate
    },
    software: mapped
  };
};

if (grid) {
  const loadCatalog = async () => {
    try {
      return await fetchSupabaseCatalog();
    } catch (_) {
      // Preserve resilience: use the committed static catalogue when the API is unavailable.
      console.warn('[Linux Software Lab] Supabase catalogue unavailable; using static JSON fallback.');
      return await fetchStaticCatalog();
    }
  };
  loadCatalog()
    .then(data => {
      if (!data || data.schemaVersion !== 2 || !Array.isArray(data.software)) {
        throw new Error('Struktur katalog tidak sesuai dengan versi skema yang didukung.');
      }
      pageSize = Number.isInteger(data.catalog?.pageSize) && data.catalog.pageSize > 0 ? Math.min(100, data.catalog.pageSize) : 12;
      software = data.software
        .filter(app => app && typeof app.id === 'string' && typeof app.name === 'string')
        .map(app => makeSearchIndex({ ...app }));
      fillCatalogControls();
      updateCatalogOverview();
      catalogLoaded = true;
      applyURLState();
      refresh(false);
    })
    .catch(error => {
      grid.innerHTML = '<div class="empty-state"><strong>Katalog belum dapat dimuat.</strong><span>' +
        escapeHTML(error.message || 'Periksa koneksi dan coba muat ulang halaman.') + '</span></div>';
      if (resultCount) resultCount.textContent = 'Katalog tidak tersedia';
      if (paginationSummary) paginationSummary.textContent = '';
      if (loadMoreButton) loadMoreButton.hidden = true;
    });
}
})();