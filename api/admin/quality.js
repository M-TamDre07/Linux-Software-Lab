const { json, method, requireAdmin, sb, genericFailure } = require('./_shared');
module.exports = async function handler(req, res) {
  if (!method(req, res, 'GET')) return;
  try {
    await requireAdmin(req);
    const reports = await sb('catalog_quality_runs?select=id,source_commit_sha,algorithm_version,entry_count,overall_score,recommendation,finding_count,severity_counts,created_at&order=created_at.desc&limit=1');
    if (!Array.isArray(reports)) return json(res, 502, { error: 'invalid_quality_response' });
    if (!reports.length) return json(res, 200, { report: null, findings: [] });
    const report = reports[0];
    const findings = await sb('catalog_quality_findings?select=software_id,rule_code,severity,deduction,message&run_id=eq.' + encodeURIComponent(report.id) + '&order=created_at.asc&limit=500');
    return json(res, 200, { report, findings: Array.isArray(findings) ? findings : [] });
  } catch (error) {
    return genericFailure(res, error);
  }
};
