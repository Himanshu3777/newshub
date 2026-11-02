# NewsVerify AI — AI-Powered News Aggregator & Fact-Checking Platform

Django + DRF + PostgreSQL (SQLite local fallback) + Celery/Redis + Bootstrap 5.

## What it does
- Fetches **metadata only** from 17 official RSS feeds (NDTV, The Hindu, Indian Express, Hindustan Times, India Today, Times of India, Zee News, News18, Moneycontrol, LiveMint, ABP Live, BBC News, Al Jazeera, DW News, The Guardian + Aaj Tak & Dainik Jagran, whose feeds are currently broken upstream). No paywall/CAPTCHA bypass, no full-article copying. Every story links to its publisher.
- Cleans, deduplicates (URL + normalized title + fingerprint + similarity), categorizes into 13 categories, extracts keywords/entities, detects language.
- Sensitive detection: phone, email, Aadhaar-like, PAN, bank patterns — **masked only, raw PII never stored** — high severity goes to human moderation.
- Verification: claim extraction → Google Fact Check Tools API (if `GOOGLE_FACTCHECK_API_KEY` set) + cross-publisher coverage → conservative status. Repetition alone never = Verified.
- Public site: Home, News, Search, Sources, Fact Check, Data Analysis, Verification Dashboard, About, Methodology, Contact/Correction.
- REST API: `/api/articles/`, `/api/categories/`, `/api/sources/`, `/api/verifications/`, `/api/evidence/`, `/api/stats/`, `/api/search/`, `/api/feedback/`, `/api/corrections/` (docs in `docs/01_SRS_ARCHITECTURE.md` and `docs/API.md`)

## Local run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_sources
python manage.py fetch_news
python manage.py verify_news --limit 20
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/ · Admin http://127.0.0.1:8000/admin/ · Health http://127.0.0.1:8000/health/

## AI content & images (free API ecosystem)
Original briefs and covers are generated through the built-in **AI Router**
(`airouter` app): quota-aware, dynamically ranked free providers with a
zero-billing cost guard — paid APIs (DeepSeek, Ideogram) are permanently
disabled. Local Composer + SVG illustration are the guaranteed fallbacks.
Staff dashboard: `/ai/`. Full details: `docs/FREE_API_ECOSYSTEM.md`.

## Useful commands
```bash
python manage.py fetch_loop --minutes 30   # auto-fetch forever (local)
python manage.py generate_covers           # backfill AI cover photos
python manage.py backup_data               # JSON backup into backups/
python manage.py validate_data --strict    # read-only data-integrity check
```

## Tests
```bash
python manage.py test
```
63 tests: ingestion, dedup, PII masking, verification, quarantine, AI router
(fallback/quota/cooldown/cache/paid-blocking), API security, locking, pages.

## Documentation
- `docs/ARCHITECTURE.md` — system design and data flow
- `docs/API_DOCUMENTATION.md` — REST API reference
- `docs/FREE_API_ECOSYSTEM.md` — provider registry, quotas, zero-billing rules
- `docs/SECURITY.md` — security model and audit results
- `docs/TESTING.md` — how to run and extend tests
- `docs/USER_GUIDE.md` — using the site and admin
- `docs/KNOWN_LIMITATIONS.md` — honest list of what is not done / upstream issues
- `LOCAL_SETUP.md` — Windows + pgAdmin local setup

## Production (Render)
Blueprint in `render.yaml`. Set `DATABASE_URL` (Neon/Postgres), `SECRET_KEY`, optional `GOOGLE_FACTCHECK_API_KEY`. Build runs `build.sh` (migrate + seed + first fetch). Start: gunicorn (see render.yaml). Celery worker/beat are in `Procfile` for platforms that support them; on Render free tier the app runs with `CELERY_TASK_ALWAYS_EAGER=True` and hourly fetch can be triggered via a Render cron hitting the staff fetch endpoint or a scheduled `fetch_news` job.

## Limitations (honest)
- Without a Google Fact Check API key, verification is heuristic + cross-source and most claims remain Unverified / Needs Human Review — by design, we do not fake verification.
- Aaj Tak / Dainik Jagran RSS endpoints change frequently; failures are logged in FetchingLog and never break other sources.
