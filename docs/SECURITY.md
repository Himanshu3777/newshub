# NewsHub — Security

## Secrets
- All keys live only in environment variables / `.env` (git-ignored). The repo
  and its full Git history were scanned for real key patterns: **0 matches**.
- Keys pasted into chat are treated as exposed and must be rotated; they are
  never stored in code, docs, or memory.
- Production fails to start if `SECRET_KEY` is unset while `DEBUG=False`.

## Settings hardening (newsverify/settings.py)
- `DEBUG` default is **False**; local dev opts in via `.env`.
- `ALLOWED_HOSTS` has no wildcard default in production.
- With `DEBUG=False`: SSL redirect, secure session/CSRF cookies, HSTS 1 year.
- Password validators: similarity + minimum length 10 + common + numeric.

## Application controls
- CSRF middleware on all forms; SecurityMiddleware + clickjacking protection.
- Rate limiting: DRF anon throttle (120/min), POST throttle middleware
  (30/min per IP on `/api/`, `/check-claim/`, `/contact/`).
- Permissions: sensitive findings, fetch and verify triggers are admin-only;
  public API writes are create-only on feedback/corrections.
- **Mass-assignment fixed (2026-11-02 audit):** feedback `is_resolved` and
  correction `status` are read-only through the API — users cannot mark their
  own submissions resolved/accepted. Regression tests in `api/test_security.py`.
- No eval/exec/pickle/mark_safe/csrf_exempt/`verify=False`/raw SQL/file uploads
  anywhere in the codebase (scanned).
- PII: detected patterns (phone/email/Aadhaar-like/PAN/bank) are masked before
  storage — including the internal RSS summary — and findings store masked
  text only. Logs record counts and statuses, not raw PII.
- AI: zero-billing cost guard runs before every external provider call; paid
  providers (DeepSeek, Ideogram) are disabled in the registry and blocked by
  the guard; OpenRouter is restricted to `:free` models. A test proves a paid
  provider is never called even when all free providers fail.
- Admin brute-force: protected by Django auth + strong password validators +
  POST rate limiting. (Dedicated lockout tooling like django-axes is not
  installed — see KNOWN_LIMITATIONS.md.)

## Response headers (verified live in production mode)
HSTS (1 year, preload), X-Content-Type-Options: nosniff, X-Frame-Options: DENY,
Referrer-Policy: same-origin, Cross-Origin-Opener-Policy: same-origin, secure
cookies, HTTP→HTTPS redirect — all confirmed on a real HTTPS response.
A Content-Security-Policy header is not set yet: the templates rely on inline
styles, so a strict CSP needs a template refactor first (tracked in
KNOWN_LIMITATIONS.md).

## Audit history
- 2026-11-02: full security review — 1 bug found (mass-assignment) and fixed;
  hostile-input probe tests added (SQLi, XSS, CSRF, auth, rate-limit flood) — all pass;
  dependency audit (pip-audit): no known vulnerabilities;
  `manage.py check --deploy` in production mode: 0 issues; dependency check clean.
