'use strict';

const {
  getConfig,
  hmac,
  constantTimeEqual,
  telegramWebhookSecret,
  telegramRequest,
  supabaseRequest,
  getTelegramBot,
  assertUserIsGroupMember,
  isGroupMember,
  sendTelegramMessage,
  jsonResponse,
} = require('./_lib/admin-telegram');

function getWebhookHeader(req) {
  return String(req.headers['x-telegram-bot-api-secret-token'] || '');
}

async function handleMemberUpdate(config, update) {
  const change = update.chat_member;
  if (!change || !change.chat || Number(change.chat.id) !== config.groupId ||
      !change.new_chat_member || !change.new_chat_member.user) return;

  const telegramUserId = Number(change.new_chat_member.user.id);
  if (!Number.isSafeInteger(telegramUserId) || telegramUserId <= 0) return;
  if (isGroupMember(change.new_chat_member)) return;

  const links = await supabaseRequest(
    config,
    '/rest/v1/lsl_admin_telegram_links?select=user_id&telegram_user_id=eq.' +
      encodeURIComponent(telegramUserId)
  );
  if (!Array.isArray(links) || !links.length) return;

  for (const link of links) {
    if (!link || typeof link.user_id !== 'string') continue;
    await supabaseRequest(
      config,
      '/rest/v1/lsl_admin_otp_verified_sessions?user_id=eq.' +
        encodeURIComponent(link.user_id),
      { method: 'DELETE' }
    );
    await supabaseRequest(
      config,
      '/rest/v1/lsl_admin_otp_challenges?user_id=eq.' +
        encodeURIComponent(link.user_id) + '&consumed_at=is.null',
      { method: 'PATCH', body: { consumed_at: new Date().toISOString() } }
    );
  }
}

async function handlePairingMessage(config, update) {
  const message = update.message;
  if (!message || !message.chat || message.chat.type !== 'private' ||
      !message.from || message.from.is_bot === true ||
      Number(message.chat.id) !== Number(message.from.id) ||
      typeof message.text !== 'string') return;

  const match = message.text.trim().match(/^\/start(?:@\w+)?\s+([A-Za-z0-9_-]{24,64})$/);
  if (!match) return;

  const tokenHash = hmac(config.serviceKey, 'telegram-link|' + match[1]);
  const telegramUserId = Number(message.from.id);
  const bot = await getTelegramBot(config);

  try {
    await assertUserIsGroupMember(config, telegramUserId, bot.id);
  } catch (_) {
    await sendTelegramMessage(
      config,
      telegramUserId,
      'Akun Telegram ini belum terdaftar sebagai anggota grup admin LISO LAB. Hubungi pengelola grup.'
    ).catch(() => {});
    return;
  }

  const linked = await supabaseRequest(config, '/rest/v1/rpc/consume_lsl_admin_telegram_link', {
    method: 'POST',
    body: {
      p_token_hash: tokenHash,
      p_telegram_user_id: telegramUserId,
    },
  });

  if (linked === true) {
    await sendTelegramMessage(
      config,
      telegramUserId,
      'Akun Telegram berhasil ditautkan ke login admin LISO LAB. Kembali ke halaman admin, perbarui status tautan, lalu minta kode OTP.'
    );
  } else {
    await sendTelegramMessage(
      config,
      telegramUserId,
      'Tautan ini tidak berlaku atau sudah kedaluwarsa. Buat tautan baru dari halaman login admin LISO LAB.'
    ).catch(() => {});
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return jsonResponse(res, 405, { error: 'METHOD_NOT_ALLOWED' });
  const config = getConfig();
  if (!config) return jsonResponse(res, 503, { error: 'WEBHOOK_NOT_CONFIGURED' });

  const expected = telegramWebhookSecret(config.botToken);
  if (!constantTimeEqual(getWebhookHeader(req), expected)) {
    return jsonResponse(res, 401, { error: 'INVALID_WEBHOOK_SECRET' });
  }

  let update = req.body;
  if (typeof update === 'string') {
    try { update = JSON.parse(update); } catch (_) { update = null; }
  }
  if (!update || typeof update !== 'object' || Array.isArray(update)) {
    return jsonResponse(res, 400, { error: 'INVALID_UPDATE' });
  }

  try {
    if (update.chat_member) await handleMemberUpdate(config, update);
    if (update.message) await handlePairingMessage(config, update);
    return jsonResponse(res, 200, { ok: true });
  } catch (_) {
    return jsonResponse(res, 503, { error: 'WEBHOOK_TEMPORARY_FAILURE' });
  }
};