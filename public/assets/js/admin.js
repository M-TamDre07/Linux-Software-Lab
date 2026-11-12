(() => {
  'use strict';

  const config = window.LSL_SUPABASE_CONFIG;
  const SESSION_KEY = 'lsl-admin-session-v2';
  const SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60;
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

  const discardStoredSession = () => {
    try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
  };

  const readSession = () => {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const now = Math.floor(Date.now() / 1000);
      const valid = parsed && typeof parsed.access_token === 'string'
        && parsed.access_token.length > 0
        && typeof parsed.refresh_token === 'string'
        && parsed.refresh_token.length > 0
        && typeof parsed.expires_at === 'number'
        && Number.isFinite(parsed.expires_at)
        && typeof parsed.authenticated_at === 'number'
        && Number.isFinite(parsed.authenticated_at)
        && parsed.authenticated_at <= now
        && Math.floor(Date.now() / 1000) - parsed.authenticated_at < SESSION_MAX_AGE_SECONDS;
      if (!valid) {
        discardStoredSession();
        return null;
      }
      return parsed;
    } catch (_) {
      discardStoredSession();
      return null;
    }
  };

  const storeSession = (value) => {
    session = value;
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(value));
    } catch (_) {
      session = value;
    }
  };

  const clearSession = () => {
    session = null;
    try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
  };

  const clearDashboardData = () => {
    catalogRows = [];
    $('#catalogRows').replaceChildren();
    $('#qualityFindingRows').replaceChildren();
    ['#metricTotal', '#metricPublished', '#metricUnpublished', '#metricTesting',
      '#qualityScore', '#qualityRecommendation', '#qualityEntries', '#qualityFindingCount',
      '#qualityCommit', '#qualityCreatedAt'].forEach((selector) => {
      const element = $(selector);
      if (element) element.textContent = '—';
    });
    $('#catalogCount').textContent = 'Data dibersihkan karena sesi tidak aktif.';
    $('#databaseStatus').textContent = 'Tidak terhubung';
    $('#databaseDetail').textContent = 'Masuk kembali untuk memuat data.';
    $('#qualityReportStatus').textContent = 'Sesi tidak aktif';
  };

  const otpPanel = $('#otpPanel');
  const otpMessage = $('#otpInstruction');
  const otpForm = $('#telegramOtpForm');
  const otpCode = $('#telegramOtpCode');
  const otpPairingControls = $('#telegramPairingControls');
  const otpControls = $('#telegramOtpControls');
  const pairingLink = $('#telegramPairingLink');
  const otpExpiryNote = $('#otpExpiryNote');

  const otpRequest = async (action, payload = {}) => {
    await freshSession();
    const call = async () => {
      const response = await fetch('/api/admin-telegram-otp', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + session.access_token,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ action, ...payload }),
        cache: 'no-store',
        credentials: 'omit',
        redirect: 'error',
      });
      const raw = await response.text();
      let result = null;
      try { result = raw ? JSON.parse(raw) : null; } catch (_) {}
      if (!response.ok) {
        const error = new Error(result && result.error ? result.error : 'Verifikasi Telegram gagal.');
        error.status = response.status;
        throw error;
      }
      return result;
    };
    try {
      return await call();
    } catch (error) {
      if (error.status !== 401) throw error;
      await refreshSession();
      return call();
    }
  };

  const showOtpPanel = (linked) => {
    loginPanel.hidden = true;
    dashboardPanel.hidden = true;
    otpPanel.hidden = false;
    otpPairingControls.hidden = linked;
    otpControls.hidden = !linked;
    otpForm.hidden = true;
    pairingLink.hidden = true;
    otpMessage.textContent = linked
      ? 'Akun Telegram telah ditautkan. Minta kode OTP, lalu masukkan enam digit yang dikirim bot ke chat pribadi.'
      : 'Tautkan akun Telegram terlebih dahulu. Kode hanya dikirim ke akun yang terdaftar dan menjadi anggota grup admin.';
  };

  const checkOtpStatus = async () => {
    const result = await otpRequest('status');
    if (!result || typeof result.linked !== 'boolean' || typeof result.verified !== 'boolean') {
      throw new Error('Status OTP tidak valid.');
    }
    return result;
  };

  const continueAfterPassword = async () => {
    await verifyAdmin();
    const state = await checkOtpStatus();
    if (state.verified) {
      otpPanel.hidden = true;
      loginPanel.hidden = true;
      dashboardPanel.hidden = false;
      await loadCatalog();
      return;
    }
    showOtpPanel(state.linked);
    setMessage(state.linked
      ? 'Password benar. Verifikasi kedua melalui Telegram diperlukan sebelum dashboard dibuka.'
      : 'Password benar. Hubungkan akun Telegram terlebih dahulu untuk mengaktifkan OTP.', 'info');
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
    if (!session || !session.refresh_token) {
      const error = new Error('Sesi berakhir. Silakan masuk kembali.');
      error.status = 401;
      throw error;
    }
    const now = Math.floor(Date.now() / 1000);
    if (!Number.isFinite(session.authenticated_at)
      || session.authenticated_at > now
      || now - session.authenticated_at >= SESSION_MAX_AGE_SECONDS) {
      clearSession();
      const error = new Error('Batas usia sesi tercapai. Silakan masuk kembali.');
      error.status = 401;
      throw error;
    }
    let renewed;
    try {
      renewed = await request('/auth/v1/token?grant_type=refresh_token', {
        method: 'POST',
        body: { refresh_token: session.refresh_token },
      });
    } catch (cause) {
      if (cause.status === 400 || cause.status === 401 || cause.status === 403) {
        clearSession();
        const error = new Error('Sesi tidak dapat diperbarui. Silakan masuk kembali.');
        error.status = 401;
        throw error;
      }
      throw cause;
    }
    const expiresIn = Number(renewed && renewed.expires_in);
    if (!renewed || typeof renewed.access_token !== 'string' || !renewed.access_token
      || typeof renewed.refresh_token !== 'string' || !renewed.refresh_token
      || !Number.isFinite(expiresIn) || expiresIn <= 0
      || (renewed.user && session.user && renewed.user.id !== session.user.id)) {
      clearSession();
      const error = new Error('Respons pembaruan sesi tidak valid. Silakan masuk kembali.');
      error.status = 401;
      throw error;
    }
    storeSession({
      access_token: renewed.access_token,
      refresh_token: renewed.refresh_token,
      expires_at: now + expiresIn,
      authenticated_at: session.authenticated_at,
      user: renewed.user || session.user || null,
    });
    return session;
  };

  const freshSession = async () => {
    if (!session) {
      const error = new Error('Sesi tidak ditemukan. Silakan masuk kembali.');
      error.status = 401;
      throw error;
    }
    const now = Math.floor(Date.now() / 1000);
    if (!Number.isFinite(session.authenticated_at)
      || session.authenticated_at > now
      || now - session.authenticated_at >= SESSION_MAX_AGE_SECONDS
      || !Number.isFinite(session.expires_at)) {
      clearSession();
      const error = new Error('Sesi tidak valid atau batas usia sesi tercapai. Silakan masuk kembali.');
      error.status = 401;
      throw error;
    }
    if (session.expires_at <= now + 45) await refreshSession();
    return session;
  };

  const authenticatedRequest = async (path) => {
    await freshSession();
    try {
      return await request(path, {}, session.access_token);
    } catch (error) {
      if (error.status !== 401) throw error;
      try {
        await refreshSession();
      } catch (refreshError) {
        if (refreshError.status === 401) {
          clearSession();
          throw refreshError;
        }
        throw refreshError;
      }
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
      await loadQualityReports();
      setMessage('Akses admin terverifikasi. Katalog berhasil dibaca; tidak ada perubahan database yang dilakukan.', 'success');
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        clearSession();
        clearDashboardData();
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

  const loadQualityReports = async () => {
    const status = $('#qualityReportStatus');
    const rowsTarget = $('#qualityFindingRows');
    const setQualityText = (selector, value) => { $(selector).textContent = value; };
    try {
      status.textContent = 'Memuat laporan…';
      const params = new URLSearchParams({
        select: 'id,source_commit_sha,algorithm_version,entry_count,overall_score,recommendation,finding_count,severity_counts,created_at',
        order: 'created_at.desc',
        limit: '1',
      });
      const reports = await authenticatedRequest('/rest/v1/catalog_quality_runs?' + params.toString());
      if (!Array.isArray(reports)) throw new Error('Respons laporan tidak valid.');
      if (reports.length === 0) {
        setQualityText('#qualityScore', '—');
        setQualityText('#qualityRecommendation', 'Belum ada');
        setQualityText('#qualityEntries', '—');
        setQualityText('#qualityFindingCount', '—');
        setQualityText('#qualityCommit', '—');
        setQualityText('#qualityCreatedAt', '—');
        rowsTarget.replaceChildren();
        const row = document.createElement('tr');
        row.appendChild(makeCell('Belum ada laporan CI tersimpan.'));
        rowsTarget.appendChild(row);
        status.textContent = 'Laporan belum tersedia';
        return;
      }
      const report = reports[0];
      setQualityText('#qualityScore', String(report.overall_score) + '/100');
      setQualityText('#qualityRecommendation', ({
        ready: 'Siap ditinjau',
        review: 'Perlu ditinjau',
        needs_attention: 'Perlu perhatian',
      })[report.recommendation] || 'Tidak diketahui');
      setQualityText('#qualityEntries', String(report.entry_count));
      setQualityText('#qualityFindingCount', String(report.finding_count));
      setQualityText('#qualityCommit', String(report.source_commit_sha || '—').slice(0, 12));
      setQualityText('#qualityCreatedAt', formatDate(report.created_at));

      const findingParams = new URLSearchParams({
        select: 'software_id,rule_code,severity,deduction,message',
        run_id: 'eq.' + report.id,
        order: 'created_at.asc',
        limit: '500',
      });
      const findings = await authenticatedRequest('/rest/v1/catalog_quality_findings?' + findingParams.toString());
      if (!Array.isArray(findings)) throw new Error('Respons temuan tidak valid.');
      rowsTarget.replaceChildren();
      if (findings.length === 0) {
        const row = document.createElement('tr');
        row.appendChild(makeCell('Tidak ada temuan untuk laporan ini.'));
        rowsTarget.appendChild(row);
      } else {
        findings.forEach((finding) => {
          const row = document.createElement('tr');
          row.appendChild(makeCell(finding.software_id || 'Katalog'));
          row.appendChild(makeCell(finding.rule_code));
          row.appendChild(makeCell(finding.severity));
          row.appendChild(makeCell(String(finding.deduction)));
          row.appendChild(makeCell(finding.message));
          rowsTarget.appendChild(row);
        });
      }
      status.textContent = 'Commit ' + String(report.source_commit_sha || '').slice(0, 12)
        + ' · ' + String(report.algorithm_version || 'algoritma tidak diketahui');
    } catch (_) {
      status.textContent = 'Laporan tidak dapat dimuat';
      rowsTarget.replaceChildren();
      const row = document.createElement('tr');
      row.appendChild(makeCell('Periksa migrasi Supabase, akses SELECT admin, dan log CI. Katalog tetap dapat dibaca terpisah.'));
      rowsTarget.appendChild(row);
    }
  };

  const showDashboard = async () => {
    if (!session) throw new Error('Sesi tidak tersedia.');
    await continueAfterPassword();
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
      const expiresIn = Number(result && result.expires_in);
      if (!result || typeof result.access_token !== 'string' || !result.access_token
        || typeof result.refresh_token !== 'string' || !result.refresh_token
        || !result.user || typeof result.user.id !== 'string' || !result.user.id
        || !Number.isFinite(expiresIn) || expiresIn <= 0) {
        throw new Error('Respons autentikasi tidak valid.');
      }
      const authenticatedAt = Math.floor(Date.now() / 1000);
      storeSession({
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        expires_at: authenticatedAt + expiresIn,
        authenticated_at: authenticatedAt,
        user: { id: result.user.id, email: result.user.email || email },
      });
      await showDashboard();
      loginForm.reset();
    } catch (error) {
      if (session && error.code !== 'NOT_ADMIN' && error.status !== 400 && error.status !== 401) {
        try {
          await verifyAdmin();
          const state = await checkOtpStatus();
          showOtpPanel(state.linked);
          setMessage(error.message || 'Verifikasi Telegram belum selesai.', 'error');
        } catch (_) {
          clearSession();
          otpPanel.hidden = true;
          dashboardPanel.hidden = true;
          loginPanel.hidden = false;
          setMessage('Login atau pemeriksaan akses gagal. Periksa akun admin dan konfigurasi layanan.', 'error');
        }
      } else {
        clearSession();
        otpPanel.hidden = true;
        dashboardPanel.hidden = true;
        loginPanel.hidden = false;
        setMessage(error.code === 'NOT_ADMIN'
          ? 'Login berhasil, tetapi akun belum tercatat sebagai admin aktif. Ikuti panduan bootstrap di docs/ADMIN_DASHBOARD.md.'
          : error.status === 400 || error.status === 401
            ? 'Login gagal. Periksa email dan kata sandi, lalu coba lagi.'
            : 'Akses admin gagal diverifikasi. Periksa konfigurasi Supabase Auth dan kebijakan RLS.', 'error');
      }
    } finally {
      setBusy(false);
    }
  });

  $('#startTelegramLinkButton').addEventListener('click', async () => {
    const button = $('#startTelegramLinkButton');
    button.disabled = true;
    try {
      const result = await otpRequest('start-link');
      if (result.linked) {
        showOtpPanel(true);
        setMessage('Akun Telegram sudah tertaut. Silakan minta kode OTP.', 'success');
      } else if (result.telegramUrl) {
        pairingLink.href = result.telegramUrl;
        pairingLink.hidden = false;
        $('#refreshTelegramLinkButton').hidden = false;
        otpExpiryNote.textContent = 'Tautan berlaku 10 menit. Buka bot dan tekan Start untuk menautkan akun.';
        setMessage('Tautan Telegram dibuat. Selesaikan langkah di Telegram, lalu perbarui status tautan.', 'success');
      } else {
        throw new Error('Bot tidak mengembalikan tautan penautan.');
      }
    } catch (error) {
      setMessage(error.message || 'Tautan Telegram gagal dibuat.', 'error');
    } finally { button.disabled = false; }
  });

  $('#refreshTelegramLinkButton').addEventListener('click', async () => {
    const button = $('#refreshTelegramLinkButton');
    button.disabled = true;
    try {
      const state = await checkOtpStatus();
      if (state.linked) {
        showOtpPanel(true);
        setMessage('Akun Telegram berhasil ditautkan. Lanjutkan dengan meminta OTP.', 'success');
      } else {
        setMessage('Tautan belum dikonfirmasi oleh bot. Pastikan kamu menekan Start pada chat pribadi bot.', 'info');
      }
    } catch (error) { setMessage(error.message || 'Status tautan belum dapat diperiksa.', 'error'); }
    finally { button.disabled = false; }
  });

  $('#requestTelegramOtpButton').addEventListener('click', async () => {
    const button = $('#requestTelegramOtpButton');
    button.disabled = true;
    try {
      await otpRequest('send-otp');
      otpForm.hidden = false;
      otpCode.focus();
      otpExpiryNote.textContent = 'Kode berlaku 5 menit, maksimal 5 percobaan, dan hanya dapat digunakan satu kali.';
      setMessage('Kode OTP dikirim ke chat pribadi Telegram yang telah ditautkan.', 'success');
    } catch (error) { setMessage(error.message || 'Kode OTP tidak dapat dikirim.', 'error'); }
    finally { button.disabled = false; }
  });

  otpForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = $('#verifyTelegramOtpButton');
    const code = otpCode.value.trim();
    if (!/^[0-9]{6}$/.test(code)) {
      setMessage('Masukkan enam digit kode OTP.', 'error');
      return;
    }
    button.disabled = true;
    try {
      await otpRequest('verify-otp', { code });
      otpCode.value = '';
      otpPanel.hidden = true;
      loginPanel.hidden = true;
      dashboardPanel.hidden = false;
      setMessage('Verifikasi Telegram berhasil. Dashboard admin telah dibuka.', 'success');
      await loadCatalog();
    } catch (error) {
      setMessage(error.message || 'Kode OTP tidak valid atau kedaluwarsa.', 'error');
    } finally { button.disabled = false; }
  });

  $('#resendTelegramOtpButton').addEventListener('click', async () => {
    $('#requestTelegramOtpButton').click();
  });

  $('#cancelOtpButton').addEventListener('click', async () => {
    try { await otpRequest('revoke-session'); } catch (_) {}
    try { if (session && session.access_token) await request('/auth/v1/logout?scope=local', { method: 'POST' }, session.access_token); } catch (_) {}
    clearSession();
    clearDashboardData();
    otpPanel.hidden = true;
    dashboardPanel.hidden = true;
    loginPanel.hidden = false;
    loginForm.reset();
    setMessage('Sesi admin telah ditutup.');
  });

  refreshButton.addEventListener('click', () => { void loadCatalog(); });
  logoutButton.addEventListener('click', async () => {
    const closingSession = session;
    logoutButton.disabled = true;
    try {
      if (closingSession && closingSession.access_token) {
        await request('/auth/v1/logout?scope=local', { method: 'POST' }, closingSession.access_token);
      }
    } catch (_) {
      // Always clear browser-held tokens even if network revocation cannot be confirmed.
    } finally {
      try { if (closingSession && closingSession.access_token) await fetch('/api/admin-telegram-otp', { method: 'POST', headers: { 'Authorization': 'Bearer ' + closingSession.access_token, 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'revoke-session' }), cache: 'no-store', credentials: 'omit' }); } catch (_) {}
      clearSession();
      clearDashboardData();
      otpPanel.hidden = true;
      dashboardPanel.hidden = true;
      loginPanel.hidden = false;
      loginForm.reset();
      logoutButton.disabled = false;
      setMessage('Sesi lokal dihapus. Jika jaringan tersedia, token refresh untuk sesi ini juga telah dicabut.');
    }
  });
  window.addEventListener('storage', (event) => {
    if (event.key !== SESSION_KEY) return;
    if (event.newValue) {
      try {
        const shared = JSON.parse(event.newValue);
        const now = Math.floor(Date.now() / 1000);
        const sameSession = shared && session
          && shared.user && session.user
          && shared.user.id === session.user.id
          && shared.authenticated_at === session.authenticated_at
          && typeof shared.access_token === 'string' && shared.access_token.length > 0
          && typeof shared.refresh_token === 'string' && shared.refresh_token.length > 0
          && Number.isFinite(shared.expires_at) && shared.expires_at > now
          && Number.isFinite(shared.authenticated_at)
          && shared.authenticated_at <= now
          && now - shared.authenticated_at < SESSION_MAX_AGE_SECONDS;
        if (sameSession) {
          // Keep token refreshes synchronized without logging out other tabs.
          session = shared;
          return;
        }
      } catch (_) {}
    }
    // A logout or account replacement in another tab clears this tab's protected view.
    clearSession();
    clearDashboardData();
    dashboardPanel.hidden = true;
    loginPanel.hidden = false;
    loginForm.reset();
    setMessage('Sesi admin berubah atau telah ditutup di tab lain. Masuk kembali untuk melanjutkan.', 'info');
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
