// NewsHub live layer: pages stay fresh without a reload.
// - Breaking ticker refreshes from the API
// - "N new stories" pill appears when fresher articles arrive; tap to prepend them
// - Trending list re-ranks from live view counts
// - Relative timestamps ("5 min ago") tick on their own
(function () {
  const POLL_MS = 90000; // 90 seconds
  const esc = (s) => { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; };
  const hhmm = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); };
  const dmon = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString([], { day: 'numeric', month: 'short' }); };

  function timeAgo(iso) {
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (isNaN(s)) return '';
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + ' min ago';
    if (s < 86400) return Math.floor(s / 3600) + ' hr ago';
    return Math.floor(s / 86400) + ' day' + (s >= 172800 ? 's' : '') + ' ago';
  }
  function tickTimes() {
    document.querySelectorAll('[data-rel-time]').forEach((el) => {
      const v = el.getAttribute('data-rel-time');
      if (v) el.textContent = timeAgo(v);
    });
  }

  function cardHTML(a) {
    const note = a.is_unconfirmed && a.source_note ? '<span class="source-note">' + esc(a.source_note) + '</span><br>' : '';
    const brief = a.ai_brief ? '<p class="card-text small text-muted">' + esc(a.ai_brief.slice(0, 150)) + '</p>' : '';
    return '<div class="card h-100 new-card-flash"><img src="/cover/' + a.id + '/" class="card-img-top card-img" alt="NewsHub AI illustration" loading="lazy">' +
      '<div class="card-body"><span class="cat-label">' + esc(a.category_name || 'News') + '</span>' +
      '<h5 class="card-title serif mt-1"><a class="text-decoration-none" style="color:var(--nh-text)" href="/news/' + esc(a.slug) + '/">' + esc(a.title) + '</a></h5>' +
      brief + note +
      '<span class="small text-muted">' + esc(a.source_name) + ' · <span data-rel-time="' + esc(a.published_at) + '">' + timeAgo(a.published_at) + '</span></span>' +
      '</div><div class="card-footer"><a href="/news/' + esc(a.slug) + '/" class="btn btn-sm btn-outline-gold">Read story</a> ' +
      '<a href="' + esc(a.source_url) + '" target="_blank" rel="noopener" class="btn btn-sm btn-link">Read at publisher →</a></div></div>';
  }
  function rowHTML(a) {
    const note = a.is_unconfirmed && a.source_note ? '<span class="source-note">' + esc(a.source_note) + '</span> ' : '';
    const brief = a.ai_brief ? '<p class="small text-muted mb-2">' + esc(a.ai_brief.slice(0, 190)) + '</p>' : '';
    return '<div class="card mb-3 new-card-flash"><div class="card-body">' +
      '<span class="cat-label">' + esc(a.category_name || 'News') + '</span>' +
      '<h4 class="serif mt-1"><a class="text-decoration-none" style="color:var(--nh-text)" href="/news/' + esc(a.slug) + '/">' + esc(a.title) + '</a></h4>' +
      brief + note +
      '<span class="small text-muted">' + esc(a.source_name) + ' · <span data-rel-time="' + esc(a.published_at) + '">' + timeAgo(a.published_at) + '</span></span>' +
      '</div></div>';
  }
  function trendHTML(t, i) {
    return '<div class="d-flex gap-3 py-2 border-bottom" style="border-color:var(--nh-border)!important"><span class="trend-num">' + (i + 1) + '</span><div>' +
      '<a class="text-decoration-none fw-semibold" style="color:var(--nh-text)" href="/news/' + esc(t.slug) + '/">' + esc(String(t.title).slice(0, 90)) + '</a><br>' +
      '<span class="small text-muted">' + esc(t.source_name) + ' · <span data-rel-time="' + esc(t.published_at) + '">' + timeAgo(t.published_at) + '</span></span></div></div>';
  }

  const feeds = Array.from(document.querySelectorAll('[data-live-feed]'));
  const ticker = document.querySelector('[data-live-ticker]');
  const trending = document.querySelector('[data-live-trending]');
  let pill = null, pending = [];

  function showPill(n) {
    if (!pill) {
      pill = document.createElement('button');
      pill.className = 'live-pill';
      pill.addEventListener('click', applyPending);
      document.body.appendChild(pill);
    }
    pill.innerHTML = '<span class="live-dot"></span> ' + n + ' nayi khabar' + (n > 1 ? 'ein' : '') + ' aayi hai — dekho';
    pill.style.display = 'block';
  }
  function applyPending() {
    pending.forEach((a) => {
      feeds.forEach((f) => {
        const wrap = document.createElement('div');
        if (f.dataset.feedStyle === 'row') { wrap.innerHTML = rowHTML(a); f.prepend(wrap.firstElementChild); }
        else { wrap.className = 'col-md-4'; wrap.innerHTML = cardHTML(a); f.prepend(wrap); }
        f.dataset.latestId = String(Math.max(parseInt(f.dataset.latestId || '0', 10), a.id));
      });
    });
    pending = [];
    if (pill) pill.style.display = 'none';
    tickTimes();
  }

  async function poll() {
    try {
      if (ticker || feeds.length) {
        const r = await fetch('/api/articles/?ordering=-published_at&page_size=10');
        if (r.ok) {
          const d = await r.json(); const items = d.results || [];
          if (ticker && items.length) {
            ticker.innerHTML = items.slice(0, 5).map((b) =>
              '<span class="badge-breaking">BREAKING</span><a class="text-decoration-none" style="color:var(--nh-text)" href="/news/' + esc(b.slug) + '/">' + esc(b.title) + '</a> <span class="text-muted">· ' + esc(b.source_name) + ' · ' + hhmm(b.published_at) + '</span>'
            ).join(' &nbsp;|&nbsp; ');
          }
          if (feeds.length) {
            const latestId = Math.max.apply(null, feeds.map((f) => parseInt(f.dataset.latestId || '0', 10)).concat([0]));
            const fresh = items.filter((a) => a.id > latestId);
            if (fresh.length) { pending = fresh; showPill(fresh.length); }
          }
        }
      }
      if (trending) {
        const r2 = await fetch('/api/articles/?ordering=-view_count&page_size=5');
        if (r2.ok) { const d2 = await r2.json(); const items = d2.results || []; if (items.length) trending.innerHTML = items.map(trendHTML).join(''); }
      }
    } catch (e) { /* offline / server busy: try again next cycle */ }
    tickTimes();
  }

  document.addEventListener('DOMContentLoaded', () => {
    tickTimes();
    setInterval(tickTimes, 30000);
    if (ticker || trending || feeds.length) { setInterval(poll, POLL_MS); }
  });
})();
