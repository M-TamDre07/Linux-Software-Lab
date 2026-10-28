const crypto = require('node:crypto');

const GROUP_ID = process.env.TELEGRAM_GROUP_ID || '-1004361361948';
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const SUPABASE_URL = (process.env.SUPABASE_URL || '').replace(/\/$/, '');
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function json(res, status, body) {
  res.status(status).setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  return res.end(JSON.stringify(body));
}
function method(req, res, expected = 'POST') {
  if (req.method !== expected) {
    res.setHeader('Allow', expected);
    json(res, 405, { error: 'method_not_allowed' });
    return false;
  }
  return true;
}
function envReady() {
  return Boolean(SUPABASE_URL && SERVICE_KEY && BOT_TOKEN);
}
function hash(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}
function codeHash(userId, code) {
  return crypto.createHmac('sha256', SERVICE_KEY).update(userId + ':' + code).digest('hex');
}
function bearer(req) {
  const value = req.headers.authorization || '';
  return value.startsWith('Bearer ') ? value.slice(7) : '';
}
function cookie(req, name) {
  const header = req.headers.cookie || '';
  for (const part of header.split(';')) {
    const index = part.indexOf('=');
    if (index < 0) continue;
    if (part.slice(0, index).trim() === name) return decodeURIComponent(part.slice(index + 1).trim());
  }
  return '';
}
async function sb(path, options = {}) {
  const response = await fetch(SUPABASE_URL + '/rest/v1/' + path, {
    method: options.method || 'GET',
    headers: {
      apikey: SERVICE_KEY,
      Authorization: 'Bearer ' + SERVICE_KEY,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      Prefer: options.prefer || 'return=representation',
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: 'no-store',
  });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) {}
  if (!response.ok) {
    const error = new Error('database_request_failed');
    error.status = response.status;
    throw error;
  }
  return data;
}
async function authUser(req) {
  const token = bearer(req);
  if (!token) return null;
  const response = await fetch(SUPABASE_URL + '/auth/v1/user', {
    headers: { apikey: process.env.SUPABASE_PUBLISHABLE_KEY || process.env.SUPABASE_ANON_KEY || '', Authorization: 'Bearer ' + token },
    cache: 'no-store',
  });
  if (!response.ok) return null;
  const user = await response.json();
  return user && typeof user.id === 'string' ? user : null;
}
async function activeAdmin(userId) {
  const rows = await sb('lsl_admin_users?select=user_id,active&user_id=eq.' + encodeURIComponent(userId) + '&active=eq.true&limit=1');
  return Array.isArray(rows) && rows.length === 1;
}
async function requireAdmin(req) {
  if (!envReady()) throw Object.assign(new Error('server_configuration_missing'), { status: 503 });
  const user = await authUser(req);
  if (!user || !(await activeAdmin(user.id))) throw Object.assign(new Error('unauthorized'), { status: 401 });
  const rawSession = cookie(req, 'lsl_admin_otp');
  if (!rawSession) throw Object.assign(new Error('otp_required'), { status: 403 });
  const sessions = await sb('lsl_admin_telegram_otp_sessions?select=auth_user_id,expires_at,revoked_at&session_hash=eq.' + hash(rawSession) + '&auth_user_id=eq.' + encodeURIComponent(user.id) + '&revoked_at=is.null&expires_at=gt.' + encodeURIComponent(new Date().toISOString()) + '&limit=1');
  if (!Array.isArray(sessions) || sessions.length !== 1) throw Object.assign(new Error('otp_required'), { status: 403 });
  return user;
}
async function telegram(methodName, body) {
  const response = await fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/' + methodName, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data || data.ok !== true) throw new Error('telegram_request_failed');
  return data.result;
}
function genericFailure(res, error) {
  if (error && (error.status === 401 || error.status === 403 || error.status === 503)) {
    return json(res, error.status, { error: error.message });
  }
  return json(res, 500, { error: 'request_failed' });
}
module.exports = { GROUP_ID, BOT_TOKEN, SUPABASE_URL, SERVICE_KEY, json, method, envReady, hash, codeHash, bearer, cookie, sb, authUser, activeAdmin, requireAdmin, telegram, genericFailure };
