# NewsHub — Architecture

## Stack
Django 5.2 + DRF · PostgreSQL (production) / SQLite (local fallback) ·
Celery + Redis (eager mode locally) · Bootstrap 5 (vendored) + vanilla JS ·
Gunicorn + WhiteNoise. No paid services anywhere.

## Apps
| App | Responsibility |
|---|---|
| `sources` | NewsSource registry (17 RSS feeds), FetchingLog (per-run health) |
| `news` | Articles, categories, tags, entities; fetcher; AI brief/cover wiring; public pages |
| `verification` | VerificationReport + Evidence; Fact Check API + cross-publisher engine |
| `moderation` | Sensitive-content detection (PII masked only) + findings |
| `feedback_app` | Public feedback + correction requests (staff fields read-only via API) |
| `core` | Site pages (home extras, fact-check, check-a-claim, methodology), rate-limit middleware, SystemLock, backup/validate commands |
| `api` | DRF viewsets/serializers (public read; admin-only sensitive data) |
| `airouter` | Free API ecosystem: registry, priority ranking, quota (daily+monthly), health/cooldown, cache, generation log, `/ai/` dashboard |

## Data flow (one story)
RSS feed → conditional fetch (ETag/Last-Modified, 1 retry) → clean/normalize →
PII masked **before storage** → dedup (URL, then title similarity per source) →
categorize + keywords/entities → social-origin detection (source-note) →
sensitive findings (masked) → AI brief via router (facts only, never publisher
text) → auto-verify (bounded batch) → AI cover via router (bounded batch,
SVG fallback) → public pages/API (quarantined stories excluded everywhere).

## Copyright rules enforced by design
Publisher article bodies and photos are never displayed. Readers see the
original NewsHub brief + NewsHub-generated cover; the internal RSS summary is
not exposed in templates **or** the public API. Every story links to its
publisher.

## Background jobs
- `fetch_news` — one run (used by Render cron every 30 min).
- `fetch_loop --minutes 30` — local auto-fetch.
- Both go through `fetch_all_sources()`, which holds the DB-backed
  `rss_fetch` SystemLock (45-min stale takeover) so runs never overlap.
- FetchingLog rows + NewsSource.last_status/last_fetched_at = job health.

## AI routing (summary)
Classify → cache → rank free providers (access level + configured capacity +
remaining quota + health) → zero-billing guard → quota/health check → single
attempt per provider → log → cache. Local Composer (text) and SVG (image)
close every chain. See `docs/FREE_API_ECOSYSTEM.md`.

## Verification search providers (pluggable)
Evidence gathering goes through `verification/providers.py`: a
`SearchProvider` registry driven by `settings.SEARCH_PROVIDERS`. The default
provider is the **Google Fact Check Tools API** (`FactCheckProvider`) — an
evidence finder that returns already-published fact-checks, never a truth
engine. **Google CSE** (`GoogleCSEProvider`) is a legacy/optional provider:
closed to new customers, discontinued 2027-01-01, enabled only when
`SEARCH_GOOGLE_CSE_ENABLED=True` *and* both CSE keys are set; its results are
stored as neutral evidence and carry no rating. Adding a future provider =
one new class + one name in `SEARCH_PROVIDERS`; nothing else in the engine
changes. Each report's summary records which providers ran and their
statuses (`[Providers: factcheck=ok, ...]`).

## Multi-signal verification rule
A final status always combines multiple evidence signals
(`verification.services.score_verification`):
- Fact-check rating false/incorrect/misleading → **False** / **Misleading**.
- Fact-check rating true/correct → **Verified** only when ≥1 independent
  publisher in our collection also covers the story; a lone true fact-check
  → **Partially Verified** (70).
- No fact-check: ≥2 cross-publisher matches → Partially Verified (55);
  exactly 1 → Unverified (30); none → Needs Human Review (15).
Repetition alone never verifies.

## Licensing gate (availability ≠ permission)
A source's technical health (`last_status`, ETag/Last-Modified) is tracked
separately from its legal right to be shown publicly (`license_status`:
`unknown` / `permitted` / `restricted`, plus `license_notes` and
`terms_url`). Public pages (`news.views.public_qs`, article detail) and the
public API (article list/search; detail returns 404) only expose articles
from `permitted` sources. New/seeded sources start at `unknown` — hidden —
until an admin checks the publisher's terms and marks them in Django admin.
