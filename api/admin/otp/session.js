const { json, method, requireAdmin, genericFailure } = require('../_shared');
module.exports = async function handler(req, res) {
  if (!method(req, res, 'GET')) return;
  try {
    const user = await requireAdmin(req);
    return json(res, 200, { ok: true, user: { id: user.id, email: user.email || '' } });
  } catch (error) {
    return genericFailure(res, error);
  }
};
