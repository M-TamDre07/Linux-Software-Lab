'use strict';

const crypto = require('node:crypto');

const TELEGRAM_GROUP_ID = -1004361361948;
const EXPECTED_TELEGRAM_BOT_ID = 8258093251;
const PRODUCTION_WEBHOOK_URL = 'https://linux-software-lab.vercel.app/api/telegram-webhook';

function getConfig() {
  const supabaseUrl = String(process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || '').replace(/\/+$/, '');
  const serviceKey = String(process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '');
  const publishableKey = String(
    process.env.SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    serviceKey
  );
  const botToken = String(process.env.TELEGRAM_BOT_TOKEN || '');

  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(supabaseUrl)) return null;
  if (!serviceKey || !publishableKey || !botToken) return null;

  return {
    supabaseUrl,
    serviceKey,
    publishableKey,
    botToken,
    groupId: TELEGRAM_GROUP_ID,
  };
}

function hmac(secret, value) {
  return crypto.createHmac('sha256', secret).update(String(value), 'utf8').digest('hex');
}

function constantTimeEqual(left, right) {
  const a = Buffer.from(String(left || ''), 'utf8');
  const b = Buffer.from(String(right || ''), 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function telegramWebhookSecret(botToken) {
  return hmac(botToken, 'lsl-lab-telegram-webhook-v1');
}

async function fetchJson(url, options, label) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      cache: 'no-store',
      signal: AbortSignal.timeout(9000),
    });
  } catch (_) {
    throw new Error(label + '_NETWORK');
  }

  let payload = null;
  try {
    const raw = await response.text();
    payload = raw ? JSON.parse(raw) : null;
  } catch (_) {
    throw new Error(label + '_INVALID_RESPONSE');
  }

  if (!response.ok) throw new Error(label + '_HTTP_' + response.status);
  return payload;
}

async function telegramRequest(config, method, payload) {
  const result = await fetchJson(
    'https://api.telegram.org/bot' + config.botToken + '/' + method,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    },
    'TELEGRAM'
  );
  if (!result || result.ok !== true) throw new Error('TELEGRAM_REJECTED');
  return result.result;
}

async function supabaseRequest(config, path, options) {
  const requestOptions = options || {};
  const headers = new Headers(requestOptions.headers || {});
  headers.set('apikey', config.serviceKey);
  headers.set('Authorization', 'Bearer ' + config.serviceKey);
  headers.set('Accept', 'application/json');
  if (requestOptions.body !== undefined) headers.set('Content-Type', 'application/json');

  const result = await fetchJson(config.supabaseUrl + path, {
    method: requestOptions.method || 'GET',
    headers,
    body: requestOptions.body === undefined ? undefined : JSON.stringify(requestOptions.body),
  }, 'SUPABASE');

  return result;
}

async function getTelegramBot(config) {
  const bot = await telegramRequest(config, 'getMe', {});
  if (!bot || Number(bot.id) !== EXPECTED_TELEGRAM_BOT_ID || typeof bot.username !== 'string') {
    throw new Error('TELEGRAM_BOT_MISMATCH');
  }
  return bot;
}

function isGroupMember(member) {
  if (!member || typeof member.status !== 'string') return false;
  if (member.status === 'creator' || member.status === 'administrator' || member.status === 'member') return true;
  return member.status === 'restricted' && member.is_member === true;
}

function isGroupAdministrator(member) {
  return Boolean(member && (member.status === 'creator' || member.status === 'administrator'));
}

async function assertBotIsGroupAdmin(config, botId) {
  const member = await telegramRequest(config, 'getChatMember', {
    chat_id: config.groupId,
    user_id: botId,
  });
  if (!isGroupAdministrator(member)) throw new Error('TELEGRAM_BOT_NOT_ADMIN');
}

async function assertUserIsGroupMember(config, telegramUserId, botId) {
  await assertBotIsGroupAdmin(config, botId);
  const member = await telegramRequest(config, 'getChatMember', {
    chat_id: config.groupId,
    user_id: telegramUserId,
  });
  if (!isGroupMember(member)) throw new Error('TELEGRAM_USER_NOT_MEMBER');
  return member;
}

async function ensureTelegramWebhook(config, botId) {
  await assertBotIsGroupAdmin(config, botId);
  const current = await telegramRequest(config, 'getWebhookInfo', {});
  const currentUrl = current && typeof current.url === 'string' ? current.url : '';

  if (currentUrl && currentUrl !== PRODUCTION_WEBHOOK_URL) {
    throw new Error('TELEGRAM_WEBHOOK_CONFLICT');
  }

  // Always set the expected secret token, including when the URL was already configured.
  await telegramRequest(config, 'setWebhook', {
    url: PRODUCTION_WEBHOOK_URL,
    secret_token: telegramWebhookSecret(config.botToken),
    allowed_updates: ['message', 'chat_member'],
    drop_pending_updates: false,
  });
}

async function sendTelegramMessage(config, chatId, text) {
  return telegramRequest(config, 'sendMessage', {
    chat_id: chatId,
    text,
    protect_content: true,
    disable_web_page_preview: true,
  });
}

function jsonResponse(res, status, payload) {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  return res.status(status).json(payload);
}

module.exports = {
  TELEGRAM_GROUP_ID,
  EXPECTED_TELEGRAM_BOT_ID,
  PRODUCTION_WEBHOOK_URL,
  getConfig,
  hmac,
  constantTimeEqual,
  telegramWebhookSecret,
  telegramRequest,
  supabaseRequest,
  getTelegramBot,
  isGroupMember,
  isGroupAdministrator,
  assertBotIsGroupAdmin,
  assertUserIsGroupMember,
  ensureTelegramWebhook,
  sendTelegramMessage,
  jsonResponse,
};