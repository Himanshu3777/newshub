# API Documentation
Base: /api/
- GET /api/articles/?search=&category__slug=&source__slug=&verification_status=&ordering=-published_at — paginated (20/page)
- GET /api/articles/{id}/
- GET /api/categories/ · GET /api/sources/
- GET /api/verifications/?status=&article= · GET /api/evidence/?report=&kind=
- GET /api/stats/ — totals, verified/disputed/unverified/needs_review, by_source/by_category/by_status
- GET /api/search/?q=
- POST /api/feedback/ {name,email,message} (public) · POST /api/corrections/ {name,email,description,article_url} (public)
- GET /api/sensitive/ (staff only)
- POST /api/fetch/run/ (staff only) · POST /api/verify/{article_id}/ (staff only)
All responses JSON. Errors: DRF standard {detail} / field errors. Throttling: anon 120/min (DRF) + POST rate-limit middleware 30/min/IP.
