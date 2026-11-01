# NewsVerify AI — AI-Powered News Aggregator & Fact-Checking Platform

Django + DRF + PostgreSQL (SQLite local fallback) + Celery/Redis + Bootstrap 5.

## What it does
- Fetches **metadata only** from official RSS feeds: BBC News, The Hindu, NDTV, Indian Express, Hindustan Times, India Today, Aaj Tak, Dainik Jagran. No paywall/CAPTCHA bypass, no full-article copying. Every story links to its publisher.
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

## Tests
```bash
python manage.py test
```

## Production (Render)
Blueprint in `render.yaml`. Set `DATABASE_URL` (Neon/Postgres), `SECRET_KEY`, optional `GOOGLE_FACTCHECK_API_KEY`. Build runs `build.sh` (migrate + seed + first fetch). Start: gunicorn (see render.yaml). Celery worker/beat are in `Procfile` for platforms that support them; on Render free tier the app runs with `CELERY_TASK_ALWAYS_EAGER=True` and hourly fetch can be triggered via a Render cron hitting the staff fetch endpoint or a scheduled `fetch_news` job.

## Limitations (honest)
- Without a Google Fact Check API key, verification is heuristic + cross-source and most claims remain Unverified / Needs Human Review — by design, we do not fake verification.
- Aaj Tak / Dainik Jagran RSS endpoints change frequently; failures are logged in FetchingLog and never break other sources.
