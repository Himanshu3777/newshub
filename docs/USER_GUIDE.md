# NewsHub — User Guide

## Reading the news
- **Home** — breaking ticker, top story, latest news (auto-updates; a gold
  pill appears when new stories arrive — click it, no refresh needed),
  trending sidebar, category sections.
- **Categories / Search** — browse by topic or search headlines. Times are
  shown as "x min pehle" and update automatically.
- **Dark/Light mode** — toggle in the header; your choice is remembered.
- Every story shows NewsHub's own short brief and its own cover image.
  "Poori story" hamesha original publisher ke link par padhein.

## Trust features
- **Fact Check page** — stories our verification flagged (false/misleading/
  disputed) are removed from the news feed and listed here with evidence.
- **Source notes** — a small note on viral/social stories that no publisher
  has confirmed yet; it disappears automatically once confirmed.
- **Check-a-Claim** — paste any claim; you get an automated assessment.
  Submissions are never published as news.
- **Methodology** — how verification works, in plain language.
- **Corrections** — spot an error? Submit a correction; the team reviews it
  (status starts as "pending" — only staff can accept/reject).

## Admin (staff)
- `/admin/` — sources, articles, verification, moderation, feedback.
- `/ai/` — AI provider dashboard: status, today's + this month's usage,
  remaining quota, generation log. Paid providers show as disabled.
- Commands: `fetch_news`, `fetch_loop --minutes 30`, `generate_covers`,
  `backup_data`, `validate_data --strict` (see README).
