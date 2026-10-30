const crypto = require('node:crypto');
const { json, method, envReady, authUser, activeAdmin, sb, codeHash, SERVICE_KEY, SUPABASE_URL, genericFailure } = require('../_shared');

module.exports = async function handler(req, res) {
  if (!method(req, res)) return;
  if (!envReady()) return json(res, 503, { error: 'otp_not_configured' });
  try {
    const user = await authUser(req);
    if (!user || !(await activeAdmin(user.id))) return json(res, 401, { error: 'unauthorized' });
    const code = req.body && typeof req.body.code === 'string' ? req.body.code.trim() : '';
    if (!/^\d{6}$/.test(code)) return json(res, 400, { error: 'invalid_code' });

    const sessionToken = crypto.randomBytes(32).toString('hex');
    const result = await fetch(SUPABASE_URL + '/rest/v1/rpc/lsl_consume_admin_telegram_otp', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        p_auth_user_id: user.id,
        p_code_hash: codeHash(user.id, code),
        p_session_hash: crypto.createHash('sha256').update(sessionToken).digest('hex'),
      }),
      cache: 'no-store',
    });
    if (!result.ok) return json(res, 503, { error: 'otp_verification_unavailable' });
    const consumed = await result.json();
    if (consumed !== true) return json(res, 401, { error: 'invalid_or_expired_code' });

    res.setHeader('Set-Cookie', 'lsl_admin_otp=' + sessionToken + '; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=28800');
    return json(res, 200, { ok: true, expires_in: 28800 });
  } catch (error) {
    return genericFailure(res, error);
  }
};
