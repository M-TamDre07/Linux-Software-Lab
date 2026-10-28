const { json, method, envReady, authUser, cookie, hash, sb, genericFailure } = require('../_shared');
module.exports = async function handler(req, res) {
  if (!method(req, res)) return;
  try {
    if (envReady()) {
      const user = await authUser(req);
      const token = cookie(req, 'lsl_admin_otp');
      if (user && token) {
        await sb('lsl_admin_telegram_otp_sessions?session_hash=eq.' + hash(token) + '&auth_user_id=eq.' + encodeURIComponent(user.id), {
          method: 'PATCH', prefer: 'return=minimal', body: { revoked_at: new Date().toISOString() },
        }).catch(() => {});
      }
    }
    res.setHeader('Set-Cookie', 'lsl_admin_otp=; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=0');
    return json(res, 200, { ok: true });
  } catch (error) {
    res.setHeader('Set-Cookie', 'lsl_admin_otp=; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=0');
    return genericFailure(res, error);
  }
};
