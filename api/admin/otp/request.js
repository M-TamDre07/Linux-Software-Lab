const crypto = require('node:crypto');
const { json, method, envReady, sb, authUser, activeAdmin, telegram, GROUP_ID, codeHash, genericFailure } = require('../_shared');

module.exports = async function handler(req, res) {
  if (!method(req, res)) return;
  if (!envReady()) return json(res, 503, { error: 'otp_not_configured' });
  try {
    const user = await authUser(req);
    if (!user || !(await activeAdmin(user.id))) return json(res, 401, { error: 'unauthorized' });

    const mappings = await sb('lsl_admin_telegram_users?select=telegram_user_id,active&auth_user_id=eq.' + encodeURIComponent(user.id) + '&active=eq.true&limit=1');
    if (!Array.isArray(mappings) || mappings.length !== 1) return json(res, 403, { error: 'otp_not_configured_for_admin' });
    const telegramUserId = String(mappings[0].telegram_user_id);

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
        chat_id: Number(telegramUserId),
        text: 'Kode verifikasi admin LISO LAB: ' + code + '\nBerlaku 5 menit. Jangan bagikan kode ini kepada siapa pun. Jika kamu tidak meminta kode ini, abaikan pesan ini.',
        protect_content: true,
      });
    } catch (_) {
      await sb('lsl_admin_telegram_otp_challenges?auth_user_id=eq.' + encodeURIComponent(user.id), {
        method: 'PATCH', prefer: 'return=minimal', body: { consumed_at: new Date().toISOString() },
      }).catch(() => {});
      return json(res, 502, { error: 'telegram_delivery_failed', hint: 'Pastikan admin sudah memulai chat pribadi dengan bot.' });
    }
    return json(res, 200, { ok: true, expires_in: 300, destination: 'telegram_private_chat' });
  } catch (error) {
    return genericFailure(res, error);
  }
};
