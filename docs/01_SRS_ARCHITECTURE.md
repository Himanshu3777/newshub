# NewsVerify AI — Phase 1-3: SRS, Architecture, DB & API Design
Date: 2026-11-01 | Owner: Himanshu Yadav | Status: Approved for build

## 1. Objective
Collect news metadata (headline, summary, source, URL, date, category) from legally permitted RSS feeds of Aaj Tak, Dainik Jagran, BBC, NDTV, The Hindu, Hindustan Times, India Today, Indian Express. Never copy full copyrighted articles or bypass paywalls/CAPTCHA. Every item links to original publisher. Extract claims, search evidence (Google Fact Check Tools API + Programmable Search when keys present), score confidence, flag sensitive PII, and present a public news site + verification dashboard + Django admin.

## 2. Roles
- Visitor: browse, search, view verification reports
- Registered user: submit feedback / correction requests
- Moderator/Admin: manage sources, review sensitive findings & unverified claims, run fetch/verify jobs (Django admin + staff dashboard)

## 3. Functional Requirements
FR1 RSS/API fetching with timeout, retry log, per-source config, activate/deactivate
FR2 Cleaning: HTML strip, unicode/whitespace normalize, language detect (hi/en heuristic), keyword + entity extraction
FR3 Dedup: exact URL, normalized title, SHA256 fingerprint, difflib similarity >=0.92 = duplicate candidate (logged, not auto-deleted)
FR4 Categorization: 13 categories via keyword classifier + feed category fallback
FR5 Sensitive detection: phone, email, Aadhaar-like, PAN, bank account patterns + minor/private keywords; severity low/medium/high/critical; masking; high-risk -> human review queue
FR6 Verification: claim extraction (sentences with entities/numbers/dates), Google Fact Check API lookup, evidence storage, confidence = f(independent sources, fact-check rating, contradictions); statuses Verified/Partially Verified/Disputed/Misleading/False/Unverified/Needs Human Review. Never Verified on repetition alone — requires >=2 independent publishers + no contradiction, else Partially/Unverified.
FR7 Search/filter: keyword, publisher, category, date, verification status; pagination, sorting
FR8 Dashboards: totals, verified/disputed/unverified/pending, source-wise stats, verification history
FR9 Feedback & corrections with moderation status
FR10 Audit log for admin actions, fetch runs, verification runs

## 4. Non-Functional
Security: env secrets only, CSRF, secure cookies in prod, rate-limit middleware (simple), input validation, DRF permissions (read public, write staff)
Performance: DB indexes on slug/url/published_at/status/category, pagination 12/20, select_related
Availability: health endpoint /health/, graceful source failure (one feed down never breaks fetch)
Legal: metadata + short summary only, source attribution, original link on every card/detail

## 5. Architecture
Frontend (Bootstrap5 + external JS Fetch) -> Django templates + DRF JSON APIs -> Services (fetcher/cleaner/dedup/sensitive/verification) -> PostgreSQL (prod) / SQLite (local dev fallback) ; Celery+Redis for scheduled fetch (sync fallback when Redis absent); Render + Gunicorn + WhiteNoise.

```
[Browser] -> [Django Views / DRF] -> [Service Layer] -> [DB]
                    |-> Celery tasks -> RSS feeds / Google Fact Check API
```

## 6. Database (ER summary)
NewsSource 1--* NewsArticle *--1 NewsCategory ; Article *--* NewsTag ; Article 1--* NewsEntity
Article 1--* VerificationReport 1--* VerificationEvidence
Article 1--* SensitiveContentFinding ; NewsSource 1--* FetchingLog
UserFeedback, CorrectionRequest (optional FK Article), AuditLog (actor, action, object)

## 7. API Design
GET /api/articles/?search=&category=&source=&status=&ordering=-published_at&page=
GET /api/articles/{id}/ ; GET /api/categories/ ; GET /api/sources/
GET /api/verifications/ ; GET /api/verifications/{id}/ ; GET /api/evidence/
GET /api/stats/ ; GET /api/search/?q=
POST /api/feedback/ ; POST /api/corrections/ (validated, rate-aware)
POST /api/fetch/run/ (staff only) ; POST /api/verify/{article_id}/ (staff only)

## 8. Third-party reality check (2026-11-01)
- RSS: BBC, Hindu, NDTV, Indian Express, HT, India Today publish public RSS. Aaj Tak / Jagran RSS endpoints change often — configured, failure is logged, not fatal.
- Google Fact Check Tools API: free with API key (GOOGLE_FACTCHECK_API_KEY), quota-limited. Without key, engine runs in evidence-heuristic mode and marks claims Unverified / Needs Human Review — honest, no fake verification.
- Google Programmable Search: requires GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID, 100 queries/day free. Optional, same graceful fallback.

## 9. Milestones
P1-3 Docs (this file) -> P4-5 Project+Models -> P6-9 Engines -> P10-12 API+Frontend -> P13-14 Tests/Security -> P15 GitHub -> P16 Render -> P17 Monitoring notes

## 10. Assumptions & Limitations
No full-text scraping. Summaries are RSS descriptions cleaned, truncated. Verification is evidence assessment, not truth oracle. Hindi language detection is heuristic (Devanagari range).
