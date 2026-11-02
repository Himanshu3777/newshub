# NewsHub — Testing

## Run everything
```bash
python manage.py test            # full suite (75 tests)
python manage.py check           # Django system checks
SECRET_KEY=<long-random> DEBUG=False ALLOWED_HOSTS=.onrender.com,localhost python manage.py check --deploy
```

## What is covered
| Area | Where |
|---|---|
| Text cleaning, dedup similarity, category, language (incl. Hindi), keywords | `news/tests.py` |
| PII detection + masking (phone/email/PAN, no raw storage) | `news/tests.py`, `news/test_audit.py` |
| Verification: no fake "verified", fact-check false, claims extraction | `news/tests.py` |
| Quarantine hidden from feed/API, warning page, source-note show/remove, claim never published, no badges | `news/tests.py` |
| RSS ingestion (mocked feedparser), URL dedup, invalid feed, retry, HTTP 304 conditional fetch | `news/test_audit.py` |
| Fetch locking + stale-lock takeover | `news/test_audit.py` |
| AI router: fallback order, cache, quota exhaustion, monthly quota, cooldown, spec error shape | `airouter/tests.py` |
| Zero-billing: paid blocked, OpenRouter `:free` only, paid never called on total failure | `airouter/tests.py` |
| API security: mass-assignment, sensitive admin-only, summary not exposed, pagination cap | `api/test_security.py`, `news/test_audit.py` |
| Pages: home, health, detail, custom 404 | `news/tests.py`, `news/test_audit.py` |
| Integration journeys: RSS→brief→verify→cover→pages→API, claim, correction, staff | `news/test_integration.py` |
| Security probes: SQLi, XSS escaping, CSRF, admin auth, rate-limit flood | `news/test_security_probes.py` |
| Data validation command | `news/test_audit.py` |

## Rules
- External APIs are always mocked — tests never consume real provider quota.
- Do not weaken a test to make it pass; fix the implementation.
