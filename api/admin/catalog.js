const { json, method, requireAdmin, sb, genericFailure } = require('./_shared');
module.exports = async function handler(req, res) {
  if (!method(req, res, 'GET')) return;
  try {
    await requireAdmin(req);
    const rows = await sb('software_catalog?select=id,slug,name,version,status,type,updated_at,published,synced_at,sort_order&order=sort_order.asc,name.asc&limit=500');
    if (!Array.isArray(rows)) return json(res, 502, { error: 'invalid_catalog_response' });
    return json(res, 200, { rows });
  } catch (error) {
    return genericFailure(res, error);
  }
};
