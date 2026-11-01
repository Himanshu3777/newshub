document.addEventListener('DOMContentLoaded', async () => {
  const el = document.getElementById('api-stats');
  if (!el) return;
  try { const r = await fetch('/api/stats/'); const d = await r.json(); el.textContent = 'API /api/stats/ → total ' + d.total + ', unverified ' + d.unverified + ', needs review ' + d.needs_review + ', sensitive pending ' + d.sensitive_pending; }
  catch(e) { el.textContent = 'API stats unavailable.'; }
});
