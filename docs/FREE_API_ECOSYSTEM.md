# NewsHub — Free API Ecosystem & Smart API Router

Zero-billing by design: **FREE_ONLY=True, ALLOW_PAID_APIS=False, AUTO_UPGRADE=False,
AUTO_PURCHASE_CREDITS=False, MAX_BILLING=0, ALLOW_PAID_FALLBACK=False.**
The cost guard (`airouter/cost_guard.py`) is checked before EVERY external call.
If all free providers fail, the system returns a controlled error / local fallback —
never a paid API.

## How routing works
Request → classify (simple/normal/premium/complex; image: svg/realistic/text_in_image)
→ cache check → candidates ranked dynamically by the priority engine
(access level P1>P2>P3>P4 + configured capacity + remaining quota + health)
→ cost guard → quota/health check → one attempt per provider → log →
on success: usage recorded, result cached. Repeated failures → cooldown.
Daily counters are per-day DB rows (Asia/Kolkata) so quotas reset automatically;
monthly caps are summed from the same rows.

## Live text chain (ranked dynamically, local = final guarantee)
Local Composer (P1, self-hosted) · Pollinations (P1, no key) · Groq (P2) ·
OpenRouter `:free` models only (P2) · Cloudflare Workers AI (P2) ·
Gemini (P3) · Mistral (P3) · Hugging Face (P3) · Qwen (P4 trial) · NVIDIA NIM (P4 trial)
**DeepSeek API: PAID → disabled** (its free chat app is not an API).

## Live image chain
Pollinations FLUX (P1, no key) → Gemini Image (P3) → Hugging Face FLUX (P3) →
Local SVG (P1, guaranteed fallback; also first choice for icons/charts/diagrams).
**Ideogram API: PAID → disabled.**

## Provider directory (verification date: 2026-11-02)
| Provider | Category | Official API | Free type | Daily limit | Monthly | Rate limit | Key? | Card? | Commercial | Priority | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Local Composer | text | in-process | FREE_OPEN_SOURCE_SELF_HOSTED | unlimited (own code) | unlimited | — | No | No | Yes | P1 | INTEGRATED |
| Local SVG | image | in-process | FREE_OPEN_SOURCE_SELF_HOSTED | unlimited (own code) | unlimited | — | No | No | Yes | P1 | INTEGRATED |
| Pollinations | text+image | https://pollinations.ai | FREE_WITH_FAIR_USE | UNKNOWN (config cap 500) | UNKNOWN | fair use | Optional | No | Per terms | P1 | INTEGRATED (live, no key) |
| Groq | text | https://console.groq.com/docs | FREE_HIGH_QUOTA | UNKNOWN (config cap 500) | UNKNOWN | per console | Yes | No | Yes | P2 | INTEGRATED (needs key) |
| OpenRouter | text | https://openrouter.ai/docs | FREE_HIGH_QUOTA | UNKNOWN (config cap 200) | UNKNOWN (config cap 1000) | per account | Yes | No | Per model | P2 | INTEGRATED (needs key; :free models only) |
| Cloudflare Workers AI | text | https://developers.cloudflare.com/workers-ai | FREE_HIGH_QUOTA | free neuron allocation (config cap 300) | UNKNOWN | per account | Token+Account ID | No | Yes | P2 | INTEGRATED (needs token) |
| Google Gemini | text+image | https://ai.google.dev/gemini-api/docs | FREE_LIMITED | UNKNOWN (config cap 200) | UNKNOWN | per AI Studio | Yes | No | Yes | P3 | INTEGRATED (needs key) |
| Mistral | text | https://docs.mistral.ai | FREE_LIMITED | UNKNOWN (config cap 100) | UNKNOWN | per plan | Yes | No | Yes | P3 | INTEGRATED (needs key) |
| Hugging Face | text+image | https://huggingface.co/docs/api-inference | FREE_LIMITED | UNKNOWN (config cap 100/50) | free credits (config cap 500) | per account | Yes | No | Per model licence | P3 | INTEGRATED (needs token) |
| Qwen (DashScope) | text | https://www.alibabacloud.com/help/en/model-studio | FREE_TRIAL | new-account quota (config cap 100) | UNKNOWN | per account | Yes | UNKNOWN | Per terms | P4 | INTEGRATED (needs key) |
| NVIDIA NIM | text | https://docs.api.nvidia.com | FREE_TRIAL | credits (config cap 100) | UNKNOWN | per account | Yes | No | Per terms | P4 | INTEGRATED (needs key) |
| DeepSeek API | text | https://api-docs.deepseek.com | PAID | — | — | — | Yes | Yes | Yes | P5 | DISABLED (zero-billing) |
| Ideogram API | image | https://developer.ideogram.ai | PAID | — | — | — | Yes | Yes | Yes | P5 | DISABLED (zero-billing) |
| Publisher RSS (17) | news | per publisher | FREE_WITH_FAIR_USE | fair use | fair use | polite polling | No | No | Attribution; no full-text republication | P1 | INTEGRATED (live) |
| Guardian Open Platform | news | https://open-platform.theguardian.com/documentation | FREE_LIMITED | UNKNOWN | UNKNOWN | per key | Yes | No | Attribution; limited | P3 | REGISTERED (later phase) |
| GNews | news | https://gnews.io/docs/v4 | FREE_LIMITED | small free quota | UNKNOWN | per plan | Yes | No | Free tier restricts commercial use | P3 | REGISTERED (later phase) |
| Wikipedia/Wikimedia | search | https://www.mediawiki.org/wiki/API:Main_page | FREE_WITH_FAIR_USE | fair use | fair use | fair use | No | No | CC BY-SA | P1 | REGISTERED (later phase) |
| LibreTranslate | translation | https://docs.libretranslate.com | FREE_OPEN_SOURCE_SELF_HOSTED | self-hosted unlimited | — | — | Self-host: No | No | AGPL (self-hosted) | P1 | REGISTERED (later phase) |
| MyMemory | translation | https://mymemory.translated.net/doc/spec.php | FREE_LIMITED | small free quota | UNKNOWN | per terms | No | No | Per terms | P3 | REGISTERED (later phase) |
| Open-Meteo | weather | https://open-meteo.com/en/docs | FREE_WITH_FAIR_USE | fair use | fair use | fair use | No | No | Check terms (non-commercial free) | P1 | REGISTERED (later phase) |
| Frankfurter | currency | https://frankfurter.dev | FREE_WITH_FAIR_USE | fair use | fair use | fair use | No | No | ECB reference rates | P1 | REGISTERED (later phase) |

"UNKNOWN" means the official free limit was not stated in a form we rely on;
the router therefore uses the conservative configured cap from `.env`
(e.g. `GEMINI_DAILY_LIMIT=200`). Caps are configuration, never hard-coded logic.

## Keys (all in `.env`, never in code/chat/frontend)
GEMINI_API_KEY · GROQ_API_KEY · OPENROUTER_API_KEY · CLOUDFLARE_ACCOUNT_ID ·
CLOUDFLARE_API_TOKEN · MISTRAL_API_KEY · HUGGINGFACE_API_KEY (or HF_TOKEN) ·
QWEN_API_KEY · NVIDIA_API_KEY · POLLINATIONS_API_KEY (optional) ·
GUARDIAN_API_KEY · GNEWS_API_KEY (later phases)

## Dashboard & tests
- Staff dashboard: `/ai/` (status, day+month usage, caps, generation log, totals).
- Tests: `python manage.py test` — includes proof that a paid provider is
  never called even when every free provider fails.
