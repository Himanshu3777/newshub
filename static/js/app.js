// NewsVerify AI - external JS only (no inline scripts in templates)
document.addEventListener('DOMContentLoaded', async () => {
  const el = document.getElementById('live-count');
  if (el) {
    try { const r = await fetch('/api/stats/'); const d = await r.json(); el.textContent = d.total + ' stories collected · ' + d.verified + ' verified'; }
    catch(e) { el.textContent = ''; }
  }
});
