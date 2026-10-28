const crypto = require('node:crypto');
const { json, method, envReady, sb, authUser, activeAdmin, telegram, GROUP_ID, codeHash, genericFailure } = require('../_shared');

function clean(value, max = 120) { return String(value || '').replaceAll(String.fromCharCode(10), ' ').replaceAll(String.fromCharCode(13), ' ').replaceAll(String.fromCharCode(9), ' ').slice(0, max) || 'Tidak tersedia'; }
function deviceLabel(ua) { const s = String(ua || '').toLowerCase(); const os = s.includes('android') ? 'Android' : (s.includes('iphone') || s.includes('ipad')) ? 'iOS' : s.includes('windows') ? 'Windows' : s.includes('linux') ? 'Linux' : s.includes('mac os') ? 'macOS' : 'Perangkat tidak dikenal'; const browser = s.includes('firefox/') ? 'Firefox' : s.includes('edg/') ? 'Edge' : s.includes('chrome/') ? 'Chrome' : s.includes('safari/') ? 'Safari' : 'Browser tidak dikenal'; return os + ' / ' + browser; }
function maskedIp(value) { const ip = String(value || '').split(',')[0].trim(); if (!ip) return 'Tidak tersedia'; if (ip.includes(':')) return ip.split(':').slice(0, 3).join(':') + '::'; const parts = ip.split('.'); return parts.length === 4 ? parts.slice(0, 3).join('.') + '.x' : 'Tidak tersedia'; }

module.exports = async function handler(req, res) {
  if (!method(req, res)) return;
  if (!envReady()) return json(res, 503, { error: 'otp_not_configured' });
  try {
    const user = await authUser(req);
    if (!user || !(await activeAdmin(user.id))) return json(res, 401, { error: 'unauthorized' });

    const mappings = await sb('lsl_admin_telegram_users?select=telegram_user_id,active&auth_user_id=eq.' + encodeURIComponent(user.id) + '&active=eq.true&limit=1');
    if (!Array.isArray(mappings) || mappings.length !== 1) return json(res, 403, { error: 'otp_not_configured_for_admin' });
    const telegramUserId = String(mappings[0].telegram_user_id);
    const device = deviceLabel(req.headers['user-agent']);
    let city = 'Tidak tersedia';
    try { if (req.headers['x-vercel-ip-city']) city = clean(decodeURIComponent(String(req.headers['x-vercel-ip-city'])), 80); } catch (_) {}
    const region = clean(req.headers['x-vercel-ip-country-region'] || '', 80);
    const country = clean(req.headers['x-vercel-ip-country'] || '', 40);
    const location = [city, region, country].filter(x => x !== 'Tidak tersedia').join(', ') || 'Tidak tersedia';
    const ip = maskedIp(req.headers['x-forwarded-for'] || req.headers['x-real-ip']);
    const email = clean(user.email || '', 120);

    const pending = await sb('lsl_admin_telegram_otp_challenges?select=created_at,consumed_at&auth_user_id=eq.' + encodeURIComponent(user.id) + '&limit=1');
    if (Array.isArray(pending) && pending.length && !pending[0].consumed_at
      && Date.now() - Date.parse(pending[0].created_at) < 60_000) {
      return json(res, 429, { error: 'otp_rate_limited', retry_after_seconds: 60 });
    }

    const membership = await telegram('getChatMember', { chat_id: GROUP_ID, user_id: Number(telegramUserId) });
    const memberStatus = membership && membership.status;
    const isMember = ['creator', 'administrator', 'member'].includes(memberStatus)
      || (memberStatus === 'restricted' && membership.is_member === true);
    if (!isMember) return json(res, 403, { error: 'telegram_group_membership_required' });

    const code = String(crypto.randomInt(0, 1_000_000)).padStart(6, '0');
    const expiresAt = new Date(Date.now() + 5 * 60_000).toISOString();
    await sb('lsl_admin_telegram_otp_challenges?on_conflict=auth_user_id', {
      method: 'POST',
      prefer: 'resolution=merge-duplicates,return=minimal',
      body: { auth_user_id: user.id, code_hash: codeHash(user.id, code), attempts: 0, expires_at: expiresAt, consumed_at: null, created_at: new Date().toISOString() },
    });

    try {
      await telegram('sendMessage', {
        chat_id: GROUP_ID,
        text: '🔐 LISO LAB — VERIFIKASI LOGIN ADMIN\\n\\nAkun: ' + email + '\\nPerangkat: ' + device + '\\nLokasi perkiraan: ' + location + '\\nIP tersamarkan: ' + ip + '\\nWaktu server: ' + new Date().toISOString() + '\\n\\nOTP: ' + code + '\\nBerlaku 5 menit • Maksimal 5 percobaan • Sekali pakai\\n\\nJika percobaan ini tidak dikenal, jangan berikan kode dan segera cabut akses admin terkait.',
        protect_content: true,
      });
    } catch (_) {
      await sb('lsl_admin_telegram_otp_challenges?auth_user_id=eq.' + encodeURIComponent(user.id), {
        method: 'PATCH', prefer: 'return=minimal', body: { consumed_at: new Date().toISOString() },
      }).catch(() => {});
      return json(res, 502, { error: 'telegram_delivery_failed', hint: 'Pastikan admin sudah memulai chat pribadi dengan bot.' });
    }
    return json(res, 200, { ok: true, expires_in: 300, destination: 'telegram_admin_group' });
  } catch (error) {
    return genericFailure(res, error);
  }
};
