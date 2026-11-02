# NewsHub — API Documentation

Base: `/api/` · JSON · Pagination: `?page=`, `?page_size=` (default 20, **max 100**).
Anonymous rate limits: DRF anon throttle 120/min + POST 30/min per IP middleware.
Errors return JSON (`{"detail": ...}`); tracebacks/secrets are never exposed.

## Public read endpoints
| Endpoint | Description |
|---|---|
| `GET /api/articles/` | Published, non-quarantined articles. Fields include `ai_brief`, `source_name`, `source_url`, `is_unconfirmed`, `source_note`. The internal RSS `summary` is **not** exposed. Filters: `category`, `source`, `verification_status`; `search`, `ordering`. |
| `GET /api/articles/{id}/` | One article. |
| `GET /api/categories/` | Categories with article counts. |
| `GET /api/sources/` | The 17 sources. |
| `GET /api/verifications/` | Verification reports (read-only). |
| `GET /api/evidence/` | Evidence items (read-only). |
| `GET /api/stats/` | Live counts (total/verified/…). |
| `GET /api/search/?q=` | Search articles. |

## Public write endpoints (create-only; everything else is admin)
| Endpoint | Rules |
|---|---|
| `POST /api/feedback/` | Body: `name`, `email`, `message`. `is_resolved` is staff-only (read-only in API). |
| `POST /api/corrections/` | Body: `name`, `email`, `description`, optional `article`/`article_url`. `status` is a moderation decision — always starts `pending`. |

## Admin-only endpoints (IsAdminUser)
| Endpoint | Description |
|---|---|
| `GET /api/sensitive/` | Sensitive-content findings (masked text only). |
| `POST /api/fetch/run/` | Trigger a fetch run. |
| `POST /api/verify/{article_id}/` | Re-verify one article. |
| `/ai/` + `POST /ai/api/text/` | AI router dashboard + staff text generation (spec-10 JSON responses). |

## Notes
- Quarantined (false/misleading/disputed) articles never appear in list/search API.
- An OpenAPI/Swagger schema is not yet generated; this document is the
  maintained reference (see KNOWN_LIMITATIONS.md).
