'use strict';

const crypto = require('node:crypto');
const {
  getConfig,
  hmac,
  telegramRequest,
  supabaseRequest,
  getTelegramBot,
  assertUserIsGroupMember,
  ensureTelegramWebhook,
  sendTelegramMessage,
  jsonResponse,
} = require('./_lib/admin-telegram');

const SESSION_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const USER_ID_PATTERN = SESSION_ID_PATTERN;
const OTP_PATTERN = /^[0-9]{6}$/;

function setCors(req, res) {
  const origin = String(req.headers.origin || '');
  const allowedOrigins = new Set(['https://linux-software-lab.vercel.app']);
  const deploymentHost = String(process.env.VERCEL_URL || '').trim();
  const productionHost = String(process.env.VERCEL_PROJECT_PRODUCTION_URL || '').trim();
  if (deploymentHost) allowedOrigins.add('https://' + deploymentHost.replace(/^https?:\/\//, ''));
  if (productionHost) allowedOrigins.add('https://' + productionHost.replace(/^https?:\/\//, ''));

  if (origin && allowedOrigins.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  } else if (origin) {
    return false;
  }

  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  return true;
}

function parseJwtPayload(token) {
  const parts = String(token || '').split('.');
  if (parts.length !== 3) return null;
  try {
    return JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
  } catch (_) {
    return null;
  }
}

async function getIdentity(req, config) {
  const authorization = String(req.headers.authorization || '');
  if (!authorization.startsWith('Bearer ')) throw new Error('AUTH_REQUIRED');
  const accessToken = authorization.slice(7).trim();
  if (!accessToken || accessToken.length > 8192) throw new Error('AUTH_REQUIRED');

  const user = await fetch(config.supabaseUrl + '/auth/v1/user', {
    method: 'GET',
    headers: {
      apikey: config.publishableKey,
      Authorization: 'Bearer ' + accessToken,
      Accept: 'application/json',
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(9000),
  }).then(async response => {
    if (!response.ok) throw new Error('AUTH_REQUIRED');
    return response.json();
  }).catch(() => { throw new Error('AUTH_REQUIRED'); });

  const claims = parseJwtPayload(accessToken);
  const now = Math.floor(Date.now() / 1000);
  if (!claims || !user || typeof user.id !== 'string' ||
      !USER_ID_PATTERN.test(user.id) || claims.sub !== user.id ||
      claims.role !== 'authenticated' || claims.is_anonymous === true ||
      !SESSION_ID_PATTERN.test(String(claims.session_id || '')) ||
      !Number.isFinite(claims.exp) || claims.exp <= now ||
      (claims.aud !== 'authenticated' && !(Array.isArray(claims.aud) && claims.aud.includes('authenticated')))) {
    throw new Error('AUTH_REQUIRED');
  }

  const admins = await supabaseRequest(
    config,
    '/rest/v1/lsl_admin_users?select=user_id&user_id=eq.' +
      encodeURIComponent(user.id) + '&active=eq.true&limit=1'
  );
  if (!Array.isArray(admins) || admins.length !== 1) throw new Error('ADMIN_REQUIRED');

  return {
    userId: user.id,
    sessionId: claims.session_id,
    accessToken,
    email: typeof user.email === 'string' ? user.email : '',
  };
}

async function getTelegramLink(config, userId) {
  const rows = await supabaseRequest(
    config,
    '/rest/v1/lsl_admin_telegram_links?select=telegram_user_id,linked_at&user_id=eq.' +
      encodeURIComponent(userId) + '&limit=1'
  );
  return Array.isArray(rows) && rows.length === 1 ? rows[0] : null;
}

async function getVerifiedSession(config, userId, sessionId) {
  const rows = await supabaseRequest(
    config,
    '/rest/v1/lsl_admin_otp_verified_sessions?select=expires_at&user_id=eq.' +
      encodeURIComponent(userId) + '&auth_session_id=eq.' +
      encodeURIComponent(sessionId) + '&expires_at=gt.' +
      encodeURIComponent(new Date().toISOString()) + '&limit=1'
  );
  return Array.isArray(rows) && rows.length === 1 ? rows[0] : null;
}

async function beginTelegramLink(config, identity) {
  const existing = await getTelegramLink(config, identity.userId);
  if (existing) return { linked: true };

  const bot = await getTelegramBot(config);
  await ensureTelegramWebhook(config, bot.id);

  const rawPairingCode = crypto.randomBytes(32).toString('base64url');
  const pairingHash = hmac(config.serviceKey, 'telegram-link|' + rawPairingCode);
  const issued = await supabaseRequest(config, '/rest/v1/rpc/issue_lsl_admin_telegram_link', {
    method: 'POST',
    body: {
      p_user_id: identity.userId,
      p_session_id: identity.sessionId,
      p_token_hash: pairingHash,
    },
  });
  if (issued !== true) throw new Error('LINK_RATE_LIMIT');

  return {
    linked: false,
    telegramUrl: 'https://t.me/' + bot.username + '?start=' + encodeURIComponent(rawPairingCode),
    expiresIn: 600,
  };
}

async function sendOtp(config, identity) {
  const link = await getTelegramLink(config, identity.userId);
  if (!link || !Number.isSafeInteger(Number(link.telegram_user_id)) || Number(link.telegram_user_id) <= 0) {
    throw new Error('TELEGRAM_LINK_REQUIRED');
  }

  const bot = await getTelegramBot(config);
  await assertUserIsGroupMember(config, Number(link.telegram_user_id), bot.id);

  const otp = String(crypto.randomInt(100000, 1000000));
  const codeHash = hmac(
    config.serviceKey,
    'telegram-otp|' + identity.userId + '|' + identity.sessionId + '|' + otp
  );
  const issued = await supabaseRequest(config, '/rest/v1/rpc/issue_lsl_admin_otp', {
    method: 'POST',
    body: {
      p_user_id: identity.userId,
      p_session_id: identity.sessionId,
      p_code_hash: codeHash,
    },
  });
  if (issued !== true) throw new Error('OTP_RATE_LIMIT');

  try {
    await sendTelegramMessage(
      config,
      Number(link.telegram_user_id),
      'Kode OTP login Admin LISO LAB: ' + otp +
        '\nBerlaku 5 menit. Jangan bagikan kode ini kepada siapa pun. ' +
        'Jika kamu tidak meminta login, abaikan pesan ini.'
    );
  } catch (_) {
    await supabaseRequest(
      config,
      '/rest/v1/lsl_admin_otp_challenges?user_id=eq.' +
        encodeURIComponent(identity.userId) + '&auth_session_id=eq.' +
        encodeURIComponent(identity.sessionId) + '&consumed_at=is.null',
      {
        method: 'PATCH',
        body: { consumed_at: new Date().toISOString() },
      }
    ).catch(() => {});
    throw new Error('TELEGRAM_DELIVERY_FAILED');
  }

  return { sent: true, expiresIn: 300 };
}

async function verifyOtp(config, identity, otp) {
  if (!OTP_PATTERN.test(String(otp || ''))) throw new Error('OTP_INVALID');
  const codeHash = hmac(
    config.serviceKey,
    'telegram-otp|' + identity.userId + '|' + identity.sessionId + '|' + otp
  );
  const verified = await supabaseRequest(config, '/rest/v1/rpc/consume_lsl_admin_otp', {
    method: 'POST',
    body: {
      p_user_id: identity.userId,
      p_session_id: identity.sessionId,
      p_code_hash: codeHash,
    },
  });
  if (verified !== true) throw new Error('OTP_INVALID');
  const row = await getVerifiedSession(config, identity.userId, identity.sessionId);
  return { verified: true, expiresAt: row ? row.expires_at : null };
}

async function status(config, identity) {
  const [link, verification] = await Promise.all([
    getTelegramLink(config, identity.userId),
    getVerifiedSession(config, identity.userId, identity.sessionId),
  ]);
  return {
    linked: Boolean(link),
    verified: Boolean(verification),
    expiresAt: verification ? verification.expires_at : null,
  };
}

async function revokeSession(config, identity) {
  await Promise.all([
    supabaseRequest(
      config,
      '/rest/v1/lsl_admin_otp_verified_sessions?user_id=eq.' +
        encodeURIComponent(identity.userId) + '&auth_session_id=eq.' +
        encodeURIComponent(identity.sessionId),
      { method: 'DELETE' }
    ),
    supabaseRequest(
      config,
      '/rest/v1/lsl_admin_otp_challenges?user_id=eq.' +
        encodeURIComponent(identity.userId) + '&auth_session_id=eq.' +
        encodeURIComponent(identity.sessionId) + '&consumed_at=is.null',
      { method: 'PATCH', body: { consumed_at: new Date().toISOString() } }
    ),
    supabaseRequest(
      config,
      '/rest/v1/lsl_admin_telegram_link_challenges?user_id=eq.' +
        encodeURIComponent(identity.userId) + '&auth_session_id=eq.' +
        encodeURIComponent(identity.sessionId) + '&consumed_at=is.null',
      { method: 'PATCH', body: { consumed_at: new Date().toISOString() } }
    ),
  ]);
}

function mapError(error) {
  const code = String(error && error.message || '');
  if (code === 'AUTH_REQUIRED') return [401, 'Sesi login tidak valid atau telah berakhir. Masuk kembali.'];
  if (code === 'ADMIN_REQUIRED') return [403, 'Akun ini tidak memiliki akses admin aktif.'];
  if (code === 'TELEGRAM_LINK_REQUIRED') return [409, 'Akun Telegram belum ditautkan.'];
  if (code === 'TELEGRAM_USER_NOT_MEMBER') return [403, 'Akun Telegram tidak terdaftar sebagai anggota grup admin LISO LAB.'];
  if (code === 'TELEGRAM_BOT_NOT_ADMIN') return [503, 'Bot belum memiliki status administrator di grup LISO LAB.'];
  if (code === 'TELEGRAM_WEBHOOK_CONFLICT') return [503, 'Webhook bot sudah dipakai alamat lain. Periksa konfigurasi bot sebelum melanjutkan.'];
  if (code === 'TELEGRAM_BOT_MISMATCH') return [503, 'Token Telegram tidak menunjuk ke bot LISO LAB yang telah ditetapkan.'];
  if (code === 'TELEGRAM_DELIVERY_FAILED') return [503, 'Telegram tidak dapat mengirim pesan privat. Buka percakapan bot dan tekan Start, lalu coba lagi.'];
  if (code === 'LINK_RATE_LIMIT' || code === 'OTP_RATE_LIMIT') return [429, 'Batas permintaan tercapai. Coba lagi setelah beberapa menit.'];
  if (code === 'OTP_INVALID') return [400, 'Kode OTP salah, kedaluwarsa, atau sudah digunakan.'];
  if (code.startsWith('TELEGRAM_') || code.startsWith('SUPABASE_')) return [503, 'Layanan verifikasi belum dapat dihubungi. Coba lagi nanti.'];
  return [503, 'Layanan verifikasi admin belum siap. Periksa konfigurasi server.'];
}

module.exports = async function handler(req, res) {
  if (!setCors(req, res)) return jsonResponse(res, 403, { error: 'ORIGIN_NOT_ALLOWED' });
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return jsonResponse(res, 405, { error: 'METHOD_NOT_ALLOWED' });
  if (Number(req.headers['content-length'] || 0) > 8192) {
    return jsonResponse(res, 413, { error: 'REQUEST_TOO_LARGE' });
  }

  const config = getConfig();
  if (!config) return jsonResponse(res, 503, { error: 'OTP_SERVER_NOT_CONFIGURED' });

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (_) { body = null; }
  }
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return jsonResponse(res, 400, { error: 'INVALID_REQUEST' });
  }

  try {
    const identity = await getIdentity(req, config);
    const action = String(body.action || '');

    if (action === 'status') {
      const value = await status(config, identity);
      return jsonResponse(res, 200, value);
    }
    if (action === 'start-link') {
      const value = await beginTelegramLink(config, identity);
      return jsonResponse(res, 200, value);
    }
    if (action === 'send-otp') {
      const value = await sendOtp(config, identity);
      return jsonResponse(res, 200, value);
    }
    if (action === 'verify-otp') {
      const value = await verifyOtp(config, identity, body.code);
      return jsonResponse(res, 200, value);
    }
    if (action === 'revoke-session') {
      await revokeSession(config, identity);
      return jsonResponse(res, 200, { revoked: true });
    }

    return jsonResponse(res, 400, { error: 'UNKNOWN_ACTION' });
  } catch (error) {
    const [statusCode, message] = mapError(error);
    return jsonResponse(res, statusCode, { error: message });
  }
};

function setCors(req, res) {
  const origin = String(req.headers.origin || '');
  const allowedOrigins = new Set(['https://linux-software-lab.vercel.app']);
  const deploymentHost = String(process.env.VERCEL_URL || '').trim();
  const productionHost = String(process.env.VERCEL_PROJECT_PRODUCTION_URL || '').trim();
  if (deploymentHost) allowedOrigins.add('https://' + deploymentHost.replace(/^https?:\/\//, ''));
  if (productionHost) allowedOrigins.add('https://' + productionHost.replace(/^https?:\/\//, ''));

  if (origin && allowedOrigins.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  } else if (origin) {
    return false;
  }
  return true;
}