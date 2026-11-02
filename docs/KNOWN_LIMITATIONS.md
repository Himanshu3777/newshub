# NewsHub — Known Limitations (honest list)

## Upstream / external
1. **Aaj Tak & Dainik Jagran RSS feeds are broken upstream** (malformed XML /
   HTML responses). Failures are logged in FetchingLog and never block other
   sources; they will start working automatically if the publishers fix them.
2. **API keys are user-provided.** Without keys in `.env`, Gemini/Mistral/Qwen/
   Groq/OpenRouter/Cloudflare/Hugging Face/NVIDIA stay inactive; Pollinations
   (no key) + Local Composer + SVG keep the site fully functional.
3. **Free-tier limits change.** Provider limits are recorded as UNKNOWN where
   not officially stated; conservative caps are configurable in `.env`.
4. **Google CSE sunset risk (unconfirmed):** the verification search layer is
   pluggable so CSE can be replaced without redesign.

## Product / design decisions
5. **Cross-publisher duplicates are kept on purpose.** The same story from
   several publishers is retained as separate articles because the
   verification engine counts independent publisher coverage. Dedup is strict
   within a source (URL + title similarity).
6. **Local Composer briefs are rule-based** (facts + templates), so their
   language is simpler than an LLM's; Hindi briefs are template-grade, not
   literary translation.
7. **`image_url` metadata** from feeds is stored for reference but never
   displayed or hotlinked anywhere on the site or API responses (only the
   article's own cover endpoint is rendered).
8. **OpenAPI/Swagger schema is not generated yet** — `docs/API_DOCUMENTATION.md`
   is the maintained reference.
9. **Admin brute-force lockout** relies on rate limiting + strong passwords;
   a dedicated lockout app (e.g. django-axes) is not installed.
10. **Fetch lock is database-backed** and correct across processes/machines
    sharing the DB; the in-process cache used for rate limiting is per-process
    on multi-worker deployments, so limits are approximate under heavy scale.
11. **No Content-Security-Policy header yet** — templates use inline styles;
    adding a strict CSP requires refactoring those to classes first.
12. **Fetch cycle speed depends on free-provider latency.** Briefs and covers
    are generated during ingestion; a slow free image provider can stretch a
    full 17-source cycle. Mitigations in place: bounded batches (8 verifies,
    3 covers per source), provider timeouts capped at 30-45s, cooldown after
    repeated failures, and HTTP conditional fetching.
13. **Hosting/deployment is intentionally out of scope** for the current
    phase: the code is Render-ready (`render.yaml`, cron fetch service) but
    not yet deployed; production needs a cloud PostgreSQL (Neon) because a
    local pgAdmin database cannot be reached from the internet.
