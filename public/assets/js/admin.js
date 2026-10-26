(() => {
  'use strict';

  const config = window.LSL_SUPABASE_CONFIG;
  const SESSION_KEY = 'lsl-admin-session-v1';
  const $ = (selector) => document.querySelector(selector);
  const loginPanel = $('#loginPanel');
  const dashboardPanel = $('#dashboardPanel');
  const message = $('#adminMessage');
  const loginForm = $('#loginForm');
  const loginButton = $('#loginButton');
  const refreshButton = $('#refreshButton');
  const logoutButton = $('#logoutButton');
  const searchInput = $('#catalogSearch');
  const publishFilter = $('#publishFilter');
  let session = null;
  let catalogRows = [];

  const setMessage = (text, kind = 'info') => {
    message.textContent = text;
    message.dataset.kind = kind;
  };

  const setBusy = (busy) => {
    loginButton.disabled = busy;
    refreshButton.disabled = busy;
    loginButton.textContent = busy ? 'Memeriksa akses…' : 'Masuk dengan Supabase Auth';
  };

  const readSession = () => {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed.access_token === 'string'
        && typeof parsed.refresh_token === 'string'
        && typeof parsed.expires_at === 'number' ? parsed : null;
    } catch (_) {
      return null;
    }
  };

  const storeSession = (value) => {
    session = value;
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(value));
    } catch (_) {
      session = value;
    }
  };

  const clearSession = () => {
    session = null;
    try { sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
  };

  const apiUrl = (path) => {
    if (!config || typeof config.url !== 'string' || typeof config.publishableKey !== 'string') {
      throw new Error('Konfigurasi Supabase tidak tersedia.');
    }
    return config.url.replace(/\/$/, '') + path;
  };

  const parseResponse = async (response) => {
    const raw = await response.text();
    let result = null;
    try { result = raw ? JSON.parse(raw) : null; } catch (_) {}
    if (!response.ok) {
      const error = new Error('Permintaan ke layanan Supabase gagal.');
      error.status = response.status;
      error.code = result && typeof result.error_code === 'string' ? result.error_code : '';
      throw error;
    }
    return result;
  };

  const request = async (path, options = {}, accessToken = '') => {
    const headers = new Headers(options.headers || {});
    headers.set('apikey', config.publishableKey);
    headers.set('Accept', 'application/json');
    if (accessToken) headers.set('Authorization', 'Bearer ' + accessToken);
    else if (options.authorization) headers.set('Authorization', options.authorization);
    if (options.body !== undefined) headers.set('Content-Type', 'application/json');
    const response = await fetch(apiUrl(path), {
      method: options.method || 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
    });
    return parseResponse(response);
  };

  const refreshSession = async () => {
    if (!session || !session.refresh_token) throw new Error('Sesi berakhir. Silakan masuk kembali.');
    const renewed = await request('/auth/v1/token?grant_type=refresh_token', {
      method: 'POST',
      body: { refresh_token: session.refresh_token },
    });
    if (!renewed || typeof renewed.access_token !== 'string' || typeof renewed.refresh_token !== 'string') {
      throw new Error('Sesi tidak dapat diperbarui.');
    }
    storeSession({
      access_token: renewed.access_token,
      refresh_token: renewed.refresh_token,
      expires_at: Math.floor(Date.now() / 1000) + Number(renewed.expires_in || 3600),
      user: renewed.user || session.user || null,
    });
    return session;
  };

  const freshSession = async () => {
    if (!session) throw new Error('Sesi tidak ditemukan.');
    if (session.expires_at <= Math.floor(Date.now() / 1000) + 45) await refreshSession();
    return session;
  };

  const authenticatedRequest = async (path) => {
    await freshSession();
    try {
      return await request(path, {}, session.access_token);
    } catch (error) {
      if (error.status !== 401) throw error;
      await refreshSession();
      return request(path, {}, session.access_token);
    }
  };

  const verifyAdmin = async () => {
    const authUser = await authenticatedRequest('/auth/v1/user');
    if (!authUser || typeof authUser.id !== 'string') {
      throw new Error('Identitas pengguna tidak dapat diverifikasi.');
    }
    const params = new URLSearchParams({
      select: 'user_id,active,note,created_at',
      user_id: 'eq.' + authUser.id,
      active: 'eq.true',
      limit: '1',
    });
    const admins = await authenticatedRequest('/rest/v1/lsl_admin_users?' + params.toString());
    if (!Array.isArray(admins) || admins.length !== 1 || admins[0].active !== true) {
      const error = new Error('Akun ini belum memiliki izin admin aktif.');
      error.code = 'NOT_ADMIN';
      throw error;
    }
    session.user = { id: authUser.id, email: authUser.email || '' };
    storeSession(session);
    $('#adminIdentity').textContent = authUser.email || 'Akun admin terverifikasi';
  };

  const formatDate = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('id-ID', {
      dateStyle: 'medium',
      timeStyle: value.includes('T') ? 'short' : undefined,
      timeZone: 'Asia/Jakarta',
    }).format(date);
  };

  const makeCell = (text, className = '') => {
    const cell = document.createElement('td');
    cell.textContent = text == null || text === '' ? '—' : String(text);
    if (className) cell.className = className;
    return cell;
  };

  const makeBadge = (text, className) => {
    const badge = document.createElement('span');
    badge.className = 'admin-table-badge ' + className;
    badge.textContent = text;
    return badge;
  };

  const renderCatalog = () => {
    const target = $('#catalogRows');
    const needle = (searchInput.value || '').trim().toLocaleLowerCase('id-ID');
    const publishMode = publishFilter.value;
    const filtered = catalogRows.filter((row) => {
      const searchText = [row.name, row.slug, row.version, row.id].filter(Boolean).join(' ').toLocaleLowerCase('id-ID');
      if (needle && !searchText.includes(needle)) return false;
      if (publishMode === 'published' && row.published !== true) return false;
      if (publishMode === 'unpublished' && row.published === true) return false;
      return true;
    });

    target.replaceChildren();
    if (!filtered.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 6;
      td.textContent = catalogRows.length ? 'Tidak ada rekaman yang cocok dengan filter.' : 'Katalog belum memiliki rekaman.';
      tr.append(td);
      target.append(tr);
    } else {
      filtered.forEach((row) => {
        const tr = document.createElement('tr');
        const appCell = document.createElement('td');
        const appName = document.createElement('span');
        appName.className = 'admin-app-name';
        const strong = document.createElement('strong');
        strong.textContent = row.name || row.slug || row.id;
        const small = document.createElement('small');
        small.textContent = row.slug || row.id;
        appName.append(strong, small);
        appCell.append(appName);
        tr.append(
          appCell,
          makeCell(row.version),
          (() => {
            const td = document.createElement('td');
            const status = ['released', 'testing', 'planned', 'archived'].includes(row.status) ? row.status : 'unknown';
            td.append(makeBadge(status, status === 'testing' || status === 'planned' ? 'status-' + status : ''));
            return td;
          })(),
          (() => {
            const td = document.createElement('td');
            td.append(makeBadge(row.published === true ? 'Dipublikasikan' : 'Tersembunyi', row.published === true ? 'is-published' : 'is-unpublished'));
            return td;
          })(),
          makeCell(formatDate(row.updated_at)),
          makeCell(formatDate(row.synced_at)),
        );
        target.append(tr);
      });
    }

    $('#catalogCount').textContent = filtered.length + ' dari ' + catalogRows.length + ' rekaman ditampilkan.';
    $('#metricTotal').textContent = String(catalogRows.length);
    $('#metricPublished').textContent = String(catalogRows.filter((row) => row.published === true).length);
    $('#metricUnpublished').textContent = String(catalogRows.filter((row) => row.published !== true).length);
    $('#metricTesting').textContent = String(catalogRows.filter((row) => row.status === 'testing').length);
    const mostRecent = catalogRows.map((row) => row.synced_at).filter(Boolean).sort().pop();
    $('#databaseStatus').textContent = 'Terhubung';
    $('#databaseDetail').textContent = mostRecent ? 'Terakhir sinkron: ' + formatDate(mostRecent) : 'Permintaan katalog berhasil';
  };

  const loadCatalog = async () => {
    setMessage('Mengambil katalog dan memverifikasi izin admin…');
    refreshButton.disabled = true;
    try {
      const params = new URLSearchParams({
        select: 'id,slug,name,version,status,type,updated_at,published,synced_at,sort_order',
        order: 'sort_order.asc,name.asc',
        limit: '500',
      });
      const rows = await authenticatedRequest('/rest/v1/software_catalog?' + params.toString());
      if (!Array.isArray(rows)) throw new Error('Respons katalog tidak valid.');
      catalogRows = rows;
      renderCatalog();
      setMessage('Akses admin terverifikasi. Katalog berhasil dibaca; tidak ada perubahan database yang dilakukan.', 'success');
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        clearSession();
        dashboardPanel.hidden = true;
        loginPanel.hidden = false;
        setMessage('Sesi atau izin admin tidak lagi berlaku. Masuk kembali setelah memeriksa konfigurasi akses.', 'error');
      } else {
        setMessage('Katalog tidak dapat dimuat. Periksa koneksi Supabase, Data API, hak SELECT, dan kebijakan RLS.', 'error');
      }
    } finally {
      refreshButton.disabled = false;
    }
  };

  const showDashboard = async () => {
    if (!session) throw new Error('Sesi tidak tersedia.');
    await verifyAdmin();
    loginPanel.hidden = true;
    dashboardPanel.hidden = false;
    await loadCatalog();
  };

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!config || !config.url || !config.publishableKey) {
      setMessage('Konfigurasi Supabase belum tersedia. Hubungi maintainer.', 'error');
      return;
    }
    setBusy(true);
    const email = $('#adminEmail').value.trim();
    const password = $('#adminPassword').value;
    try {
      const result = await request('/auth/v1/token?grant_type=password', {
        method: 'POST',
        body: { email, password },
      });
      if (!result || typeof result.access_token !== 'string' || typeof result.refresh_token !== 'string' || !result.user) {
        throw new Error('Respons autentikasi tidak valid.');
      }
      storeSession({
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        expires_at: Math.floor(Date.now() / 1000) + Number(result.expires_in || 3600),
        user: { id: result.user.id, email: result.user.email || email },
      });
      await showDashboard();
    } catch (error) {
      clearSession();
      dashboardPanel.hidden = true;
      loginPanel.hidden = false;
      setMessage(error.code === 'NOT_ADMIN'
        ? 'Login berhasil, tetapi akun belum tercatat sebagai admin aktif. Ikuti panduan bootstrap di docs/ADMIN_DASHBOARD.md.'
        : error.status === 400 || error.status === 401
          ? 'Login gagal. Periksa email dan kata sandi, lalu coba lagi.'
          : 'Akses admin gagal diverifikasi. Periksa konfigurasi Supabase Auth dan kebijakan RLS.', 'error');
    } finally {
      setBusy(false);
    }
  });

  refreshButton.addEventListener('click', () => { void loadCatalog(); });
  logoutButton.addEventListener('click', () => {
    clearSession();
    catalogRows = [];
    dashboardPanel.hidden = true;
    loginPanel.hidden = false;
    loginForm.reset();
    setMessage('Kamu telah keluar dari sesi admin.');
  });
  searchInput.addEventListener('input', renderCatalog);
  publishFilter.addEventListener('change', renderCatalog);

  const themeButton = $('#themeToggle');
  const menuButton = $('#menuToggle');
  const nav = $('#navLinks');
  const getTheme = () => {
    try {
      const saved = localStorage.getItem('software-lab-theme');
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (_) {}
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };
  const setTheme = (theme) => {
    document.documentElement.dataset.theme = theme;
    themeButton.setAttribute('aria-label', theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap');
    themeButton.title = theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap';
  };
  setTheme(getTheme());
  themeButton.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('software-lab-theme', next); } catch (_) {}
  });
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
    nav.classList.toggle('is-open', open);
    document.body.classList.toggle('menu-open', open);
  });
  nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
    nav.classList.remove('is-open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Buka menu');
    document.body.classList.remove('menu-open');
  }));

  if (!config || typeof config.url !== 'string' || typeof config.publishableKey !== 'string') {
    loginPanel.hidden = false;
    setMessage('Konfigurasi Supabase tidak ditemukan. Halaman tidak akan mencoba login.', 'error');
  } else {
    session = readSession();
    if (session) {
      setBusy(true);
      showDashboard().catch(() => {
        clearSession();
        loginPanel.hidden = false;
        dashboardPanel.hidden = true;
        setMessage('Sesi tidak valid atau akun belum terdaftar sebagai admin aktif. Silakan masuk kembali.', 'error');
      }).finally(() => setBusy(false));
    } else {
      loginPanel.hidden = false;
      setMessage('Masuk menggunakan akun Supabase Auth yang sudah diizinkan sebagai admin.');
    }
  }
})();
