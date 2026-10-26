import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/+esm';

const $ = (selector) => document.querySelector(selector);
const state = { client: null, user: null, rows: [] };
const els = {
  notice: $('#notice'),
  loginView: $('#loginView'),
  deniedView: $('#deniedView'),
  dashboardView: $('#dashboardView'),
  loginForm: $('#loginForm'),
  loginEmail: $('#loginEmail'),
  loginPassword: $('#loginPassword'),
  loginButton: $('#loginButton'),
  currentUserId: $('#currentUserId'),
  copyUserId: $('#copyUserId'),
  deniedLogoutButton: $('#deniedLogoutButton'),
  adminEmail: $('#adminEmail'),
  logoutButton: $('#logoutButton'),
  refreshButton: $('#refreshButton'),
  exportButton: $('#exportButton'),
  statTotal: $('#statTotal'),
  statPublished: $('#statPublished'),
  statHidden: $('#statHidden'),
  statSync: $('#statSync'),
  search: $('#catalogSearch'),
  publishedFilter: $('#publishedFilter'),
  rows: $('#catalogRows'),
  resultCount: $('#resultCount'),
  recordDialog: $('#recordDialog'),
  recordJson: $('#recordJson'),
  closeRecordDialog: $('#closeRecordDialog')
};

function showView(view) {
  els.loginView.hidden = view !== 'login';
  els.deniedView.hidden = view !== 'denied';
  els.dashboardView.hidden = view !== 'dashboard';
}

function setNotice(message, kind = 'info') {
  els.notice.textContent = message;
  els.notice.dataset.kind = kind;
  els.notice.hidden = !message;
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'medium',
    timeStyle: value.includes('T') ? 'short' : undefined,
    timeZone: value.includes('T') ? 'UTC' : undefined
  }).format(date);
}

function makeCell(text, className) {
  const cell = document.createElement('td');
  cell.textContent = text == null || text === '' ? '—' : String(text);
  if (className) cell.className = className;
  return cell;
}

function currentRows() {
  const query = els.search.value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('id-ID').trim();
  const publishedFilter = els.publishedFilter.value;
  return state.rows.filter((row) => {
    const searchable = [row.id, row.slug, row.name, row.category, row.version, row.summary]
      .filter(Boolean).join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('id-ID');
    if (query && !searchable.includes(query)) return false;
    if (publishedFilter === 'published' && row.published !== true) return false;
    if (publishedFilter === 'hidden' && row.published !== false) return false;
    return true;
  });
}

function renderRows() {
  const rows = currentRows();
  els.rows.replaceChildren();
  if (!rows.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.textContent = 'Tidak ada entri yang cocok dengan filter.';
    tr.append(td);
    els.rows.append(tr);
    els.resultCount.textContent = '0 entri ditampilkan.';
    return;
  }
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    const nameCell = document.createElement('td');
    const name = document.createElement('strong');
    name.className = 'admin-row-name';
    name.textContent = row.name;
    const id = document.createElement('span');
    id.className = 'admin-row-id';
    id.textContent = row.id;
    nameCell.append(name, id);
    tr.append(nameCell);
    tr.append(makeCell(row.version));
    tr.append(makeCell(row.status));
    const publicationCell = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'admin-row-badge';
    badge.dataset.published = String(row.published === true);
    badge.textContent = row.published === true ? 'Publik' : 'Disembunyikan';
    publicationCell.append(badge);
    tr.append(publicationCell);
    tr.append(makeCell(row.updated_at));
    const actionCell = document.createElement('td');
    const action = document.createElement('button');
    action.className = 'admin-row-action';
    action.type = 'button';
    action.textContent = 'Lihat JSON';
    action.setAttribute('aria-label', 'Lihat detail data ' + row.name);
    action.addEventListener('click', () => openRecord(row.id));
    actionCell.append(action);
    tr.append(actionCell);
    els.rows.append(tr);
  });
  els.resultCount.textContent = rows.length + ' dari ' + state.rows.length + ' entri ditampilkan.';
}

function updateStats() {
  const published = state.rows.filter((row) => row.published === true).length;
  const timestamps = state.rows.map((row) => row.synced_at).filter(Boolean);
  const latest = timestamps.length ? timestamps.sort().at(-1) : null;
  els.statTotal.textContent = String(state.rows.length);
  els.statPublished.textContent = String(published);
  els.statHidden.textContent = String(state.rows.length - published);
  els.statSync.textContent = latest ? formatDate(latest) : 'Belum ada';
}

function openRecord(id) {
  const record = state.rows.find((row) => row.id === id);
  if (!record) return;
  els.recordJson.textContent = JSON.stringify(record, null, 2);
  els.recordDialog.showModal();
}

async function loadCatalog() {
  els.refreshButton.disabled = true;
  els.refreshButton.textContent = 'Memuat…';
  setNotice('Memuat semua baris katalog yang diizinkan untuk akun ini.');
  try {
    const { data, error } = await state.client
      .from('software_catalog')
      .select('id,slug,name,version,summary,description,category,status,type,platforms,tags,keywords,features,detail_url,source_url,release_url,icon,icon_image,preview_image,preview_alt,updated_at,sort_order,published,synced_at')
      .order('sort_order', { ascending: true })
      .order('name', { ascending: true });
    if (error) throw error;
    state.rows = Array.isArray(data) ? data : [];
    updateStats();
    renderRows();
    setNotice('Katalog berhasil dimuat dan dibaca melalui kebijakan database.', 'success');
  } catch (error) {
    setNotice('Gagal membaca katalog. Periksa koneksi Data API, grant SELECT, kebijakan RLS, serta status proyek Supabase. Detail: ' + (error?.message || 'kesalahan tidak diketahui'), 'error');
  } finally {
    els.refreshButton.disabled = false;
    els.refreshButton.textContent = 'Muat ulang data';
  }
}

async function resolveAccess(user) {
  state.user = user;
  const { data: admin, error } = await state.client
    .from('lsl_admin_users')
    .select('user_id,active')
    .eq('user_id', user.id)
    .maybeSingle();

  if (error) {
    showView('login');
    setNotice('Belum dapat memeriksa izin admin. Pastikan migrasi admin sudah diterapkan dan tabel lsl_admin_users dapat dibaca oleh akun terautentikasi. Detail: ' + error.message, 'error');
    return;
  }
  if (!admin || admin.active !== true) {
    els.currentUserId.textContent = user.id;
    showView('denied');
    setNotice('Login berhasil, tetapi akun ini belum memiliki izin maintainer.', 'error');
    return;
  }
  showView('dashboard');
  els.adminEmail.textContent = user.email || 'Maintainer terautentikasi';
  await loadCatalog();
}

async function signOut() {
  if (!state.client) return;
  const { error } = await state.client.auth.signOut();
  state.rows = [];
  state.user = null;
  showView('login');
  setNotice(error ? 'Sesi lokal telah ditutup, tetapi server melaporkan: ' + error.message : 'Kamu sudah keluar.', error ? 'error' : 'success');
}

async function initialize() {
  const config = window.LSL_SUPABASE_CONFIG;
  if (!config || !config.url || !config.publishableKey) {
    showView('login');
    els.loginButton.disabled = true;
    setNotice('Konfigurasi publik Supabase tidak tersedia. Periksa public/assets/js/supabase-config.js.', 'error');
    return;
  }
  state.client = createClient(config.url, config.publishableKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });

  const { data, error } = await state.client.auth.getSession();
  if (error) {
    showView('login');
    setNotice('Tidak dapat memulihkan sesi. Silakan masuk kembali. Detail: ' + error.message, 'error');
    return;
  }
  if (!data.session) {
    showView('login');
    return;
  }
  const { data: verified, error: verifyError } = await state.client.auth.getUser();
  if (verifyError || !verified.user) {
    await state.client.auth.signOut();
    showView('login');
    setNotice('Sesi tidak dapat diverifikasi oleh Supabase Auth. Silakan masuk kembali.', 'error');
    return;
  }
  await resolveAccess(verified.user);
}

els.loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.client) return;
  els.loginButton.disabled = true;
  els.loginButton.textContent = 'Memeriksa…';
  setNotice('Memeriksa sesi dan izin maintainer.');
  try {
    const { data, error } = await state.client.auth.signInWithPassword({
      email: els.loginEmail.value.trim(),
      password: els.loginPassword.value
    });
    if (error) throw error;
    if (!data.user) throw new Error('Supabase Auth tidak mengembalikan identitas pengguna.');
    els.loginPassword.value = '';
    await resolveAccess(data.user);
  } catch (error) {
    setNotice('Login tidak berhasil. Periksa email, password, status verifikasi akun, dan konfigurasi provider Email di Supabase Auth. Detail: ' + (error?.message || 'kesalahan tidak diketahui'), 'error');
  } finally {
    els.loginButton.disabled = false;
    els.loginButton.textContent = 'Masuk ke dashboard';
  }
});

els.copyUserId.addEventListener('click', async () => {
  const id = els.currentUserId.textContent;
  try {
    await navigator.clipboard.writeText(id);
    setNotice('UUID akun berhasil disalin.', 'success');
  } catch (_) {
    setNotice('Salin UUID dari teks yang tampil di panel ini.', 'info');
  }
});

els.deniedLogoutButton.addEventListener('click', signOut);
els.logoutButton.addEventListener('click', signOut);
els.refreshButton.addEventListener('click', loadCatalog);
els.search.addEventListener('input', renderRows);
els.publishedFilter.addEventListener('change', renderRows);
els.exportButton.addEventListener('click', () => {
  const payload = JSON.stringify(state.rows, null, 2);
  const blob = new Blob([payload], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'linux-software-lab-supabase-catalog.json';
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setNotice('Ekspor JSON dibuat dari data yang baru dimuat.', 'success');
});
els.closeRecordDialog.addEventListener('click', () => els.recordDialog.close());
els.recordDialog.addEventListener('click', (event) => {
  if (event.target === els.recordDialog) els.recordDialog.close();
});

const startDashboard = () => {
  initialize().catch((error) => {
    showView('login');
    setNotice('Inisialisasi dashboard gagal. Detail: ' + (error?.message || 'kesalahan tidak diketahui'), 'error');
  });
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startDashboard, { once: true });
} else {
  startDashboard();
}
