"""Provider Registry - the single source of truth for the Free API Ecosystem.

Classification (spec 2/12):
  P1 FREE (genuinely free / self-hosted / fair-use, no mandatory payment)
  P2 FREE_HIGH_QUOTA   P3 FREE_LIMITED   P4 FREE_TRIAL (expiring credits)
  P5 PAID -> DISABLED completely. The cost guard refuses to call these.

Rules honoured here:
- Limits are NEVER invented. Unknown official limits are recorded as None
  (UNKNOWN) and the router uses conservative configurable caps from .env
  (settings.AI_DAILY_LIMITS) instead.
- A provider becomes ACTIVE only when free_only_verified is True.
- DeepSeek's API is a paid balance API (its free *chat app* is not an API),
  so it is classified PAID and disabled under the zero-billing rule.
- Ideogram's API is paid, so it is disabled the same way.
"""

REGISTRY = [
    # ---------------- TEXT ----------------
    {"slug": "local", "name": "Local Composer (self-hosted)", "category": "text",
     "base_url": "in-process", "docs_url": "", "pricing_url": "",
     "auth": "none", "free_type": "FREE_OPEN_SOURCE_SELF_HOSTED", "level": 1,
     "key_env": "", "card_required": "No", "commercial": "Yes (own code)",
     "free_only_verified": True, "status_note": "Rule-based composer; final guarantee of every text chain."},
    {"slug": "pollinations", "name": "Pollinations (text + image)", "category": "text",
     "base_url": "https://text.pollinations.ai", "docs_url": "https://pollinations.ai",
     "pricing_url": "https://pollinations.ai", "auth": "none (optional key)",
     "free_type": "FREE_WITH_FAIR_USE", "level": 1, "key_env": "POLLINATIONS_API_KEY",
     "card_required": "No", "commercial": "Per Pollinations terms",
     "free_only_verified": True, "status_note": "No key needed; works today."},
    {"slug": "groq", "name": "Groq", "category": "text",
     "base_url": "https://api.groq.com/openai/v1", "docs_url": "https://console.groq.com/docs",
     "pricing_url": "https://groq.com/pricing", "auth": "api_key",
     "free_type": "FREE_HIGH_QUOTA", "level": 2, "key_env": "GROQ_API_KEY",
     "card_required": "No", "commercial": "Yes",
     "free_only_verified": True, "status_note": "Generous free tier; very fast. Needs GROQ_API_KEY."},
    {"slug": "openrouter", "name": "OpenRouter (free models only)", "category": "text",
     "base_url": "https://openrouter.ai/api/v1", "docs_url": "https://openrouter.ai/docs",
     "pricing_url": "https://openrouter.ai/models?max_price=0", "auth": "api_key",
     "free_type": "FREE_HIGH_QUOTA", "level": 2, "key_env": "OPENROUTER_API_KEY",
     "card_required": "No", "commercial": "Per model terms",
     "free_only_verified": True, "status_note": "Cost guard allows ONLY models ending in ':free'."},
    {"slug": "cloudflare", "name": "Cloudflare Workers AI", "category": "text",
     "base_url": "https://api.cloudflare.com/client/v4/accounts/{id}/ai/v1", "docs_url": "https://developers.cloudflare.com/workers-ai",
     "pricing_url": "https://developers.cloudflare.com/workers-ai/platform/pricing", "auth": "api_token+account_id",
     "free_type": "FREE_HIGH_QUOTA", "level": 2, "key_env": "CLOUDFLARE_API_TOKEN",
     "card_required": "No", "commercial": "Yes",
     "free_only_verified": True, "status_note": "Free daily neuron allocation; needs account id + token."},
    {"slug": "huggingface", "name": "Hugging Face Inference", "category": "text",
     "base_url": "https://router.huggingface.co/v1", "docs_url": "https://huggingface.co/docs/api-inference",
     "pricing_url": "https://huggingface.co/pricing", "auth": "api_key",
     "free_type": "FREE_LIMITED", "level": 3, "key_env": "HUGGINGFACE_API_KEY",
     "card_required": "No", "commercial": "Per model licence",
     "free_only_verified": True, "status_note": "Free monthly inference credits; also used for images."},
    {"slug": "gemini", "name": "Google Gemini", "category": "text",
     "base_url": "https://generativelanguage.googleapis.com/v1beta", "docs_url": "https://ai.google.dev/gemini-api/docs",
     "pricing_url": "https://ai.google.dev/pricing", "auth": "api_key",
     "free_type": "FREE_LIMITED", "level": 3, "key_env": "GEMINI_API_KEY",
     "card_required": "No", "commercial": "Yes (free tier terms)",
     "free_only_verified": True, "status_note": "Free tier via AI Studio key; also image generation."},
    {"slug": "mistral", "name": "Mistral AI", "category": "text",
     "base_url": "https://api.mistral.ai/v1", "docs_url": "https://docs.mistral.ai",
     "pricing_url": "https://mistral.ai/pricing", "auth": "api_key",
     "free_type": "FREE_LIMITED", "level": 3, "key_env": "MISTRAL_API_KEY",
     "card_required": "No", "commercial": "Yes",
     "free_only_verified": True, "status_note": "Free Experiment plan."},
    {"slug": "qwen", "name": "Qwen (Alibaba DashScope)", "category": "text",
     "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "docs_url": "https://www.alibabacloud.com/help/en/model-studio",
     "pricing_url": "https://www.alibabacloud.com/help/en/model-studio/billing-for-model-studio", "auth": "api_key",
     "free_type": "FREE_TRIAL", "level": 4, "key_env": "QWEN_API_KEY",
     "card_required": "UNKNOWN", "commercial": "Per Alibaba terms",
     "free_only_verified": True, "status_note": "New-account free quota; expires - ranked low on purpose."},
    {"slug": "nvidia", "name": "NVIDIA NIM", "category": "text",
     "base_url": "https://integrate.api.nvidia.com/v1", "docs_url": "https://docs.api.nvidia.com",
     "pricing_url": "https://build.nvidia.com", "auth": "api_key",
     "free_type": "FREE_TRIAL", "level": 4, "key_env": "NVIDIA_API_KEY",
     "card_required": "No", "commercial": "Per NVIDIA terms",
     "free_only_verified": True, "status_note": "Free API credits for developers; trial class."},
    {"slug": "deepseek", "name": "DeepSeek API", "category": "text",
     "base_url": "https://api.deepseek.com/v1", "docs_url": "https://api-docs.deepseek.com",
     "pricing_url": "https://api-docs.deepseek.com/quick_start/pricing", "auth": "api_key",
     "free_type": "PAID", "level": 5, "key_env": "DEEPSEEK_API_KEY",
     "card_required": "Yes (balance top-up)", "commercial": "Yes",
     "free_only_verified": False, "status_note": "DISABLED by zero-billing guard: the API is pay-per-use; the free chat app is not an API."},
    # ---------------- IMAGE ----------------
    {"slug": "svg", "name": "Local SVG Generator (self-hosted)", "category": "image",
     "base_url": "in-process", "docs_url": "", "pricing_url": "", "auth": "none",
     "free_type": "FREE_OPEN_SOURCE_SELF_HOSTED", "level": 1, "key_env": "",
     "card_required": "No", "commercial": "Yes (own code)",
     "free_only_verified": True, "status_note": "For icons/charts/simple graphics + final fallback. Never presented as an AI photo."},
    {"slug": "ideogram", "name": "Ideogram API", "category": "image",
     "base_url": "https://api.ideogram.ai", "docs_url": "https://developer.ideogram.ai",
     "pricing_url": "https://ideogram.ai/pricing", "auth": "api_key",
     "free_type": "PAID", "level": 5, "key_env": "IDEOGRAM_API_KEY",
     "card_required": "Yes", "commercial": "Yes",
     "free_only_verified": False, "status_note": "DISABLED by zero-billing guard: API access is paid (free web app is not an API)."},
    # ---------------- NEWS / SEARCH / UTILITY (registered; RSS already live) ----------------
    {"slug": "rss-feeds", "name": "Publisher RSS feeds (17 sources)", "category": "news",
     "base_url": "per-publisher", "docs_url": "", "pricing_url": "", "auth": "none",
     "free_type": "FREE_WITH_FAIR_USE", "level": 1, "key_env": "",
     "card_required": "No", "commercial": "Attribution + link to publisher; no full-text republication",
     "free_only_verified": True, "status_note": "INTEGRATED - NewsHub's live news collection (headline/facts only)."},
    {"slug": "guardian", "name": "The Guardian Open Platform", "category": "news",
     "base_url": "https://content.guardianapis.com", "docs_url": "https://open-platform.theguardian.com/documentation",
     "pricing_url": "https://open-platform.theguardian.com/access", "auth": "api_key",
     "free_type": "FREE_LIMITED", "level": 3, "key_env": "GUARDIAN_API_KEY",
     "card_required": "No", "commercial": "Limited; attribution required",
     "free_only_verified": True, "status_note": "Registered - free developer key; integration is a later phase."},
    {"slug": "gnews", "name": "GNews API", "category": "news",
     "base_url": "https://gnews.io/api/v4", "docs_url": "https://gnews.io/docs/v4",
     "pricing_url": "https://gnews.io/#pricing", "auth": "api_key",
     "free_type": "FREE_LIMITED", "level": 3, "key_env": "GNEWS_API_KEY",
     "card_required": "No", "commercial": "Free tier restricts commercial use - check terms",
     "free_only_verified": True, "status_note": "Registered - small free daily quota."},
    {"slug": "wikipedia", "name": "Wikipedia / Wikimedia APIs", "category": "search",
     "base_url": "https://en.wikipedia.org/w/api.php", "docs_url": "https://www.mediawiki.org/wiki/API:Main_page",
     "pricing_url": "", "auth": "none", "free_type": "FREE_WITH_FAIR_USE", "level": 1,
     "key_env": "", "card_required": "No", "commercial": "CC BY-SA content",
     "free_only_verified": True, "status_note": "Registered - background research; snippets are evidence, not proof."},
    {"slug": "libretranslate", "name": "LibreTranslate (self-hostable)", "category": "translation",
     "base_url": "https://libretranslate.com/translate", "docs_url": "https://docs.libretranslate.com",
     "pricing_url": "https://libretranslate.com", "auth": "none (self-hosted) / key (hosted)",
     "free_type": "FREE_OPEN_SOURCE_SELF_HOSTED", "level": 1, "key_env": "LIBRETRANSLATE_API_KEY",
     "card_required": "No", "commercial": "Yes (self-hosted, AGPL)",
     "free_only_verified": True, "status_note": "Registered - EN<->HI translation; later phase."},
    {"slug": "mymemory", "name": "MyMemory Translation", "category": "translation",
     "base_url": "https://api.mymemory.translated.net/get", "docs_url": "https://mymemory.translated.net/doc/spec.php",
     "pricing_url": "", "auth": "none (email raises quota)", "free_type": "FREE_LIMITED", "level": 3,
     "key_env": "", "card_required": "No", "commercial": "Per terms",
     "free_only_verified": True, "status_note": "Registered - small free daily quota."},
    {"slug": "open-meteo", "name": "Open-Meteo", "category": "weather",
     "base_url": "https://api.open-meteo.com/v1/forecast", "docs_url": "https://open-meteo.com/en/docs",
     "pricing_url": "", "auth": "none", "free_type": "FREE_WITH_FAIR_USE", "level": 1,
     "key_env": "", "card_required": "No", "commercial": "Non-commercial free; check terms",
     "free_only_verified": True, "status_note": "Registered - weather widgets; later phase."},
    {"slug": "frankfurter", "name": "Frankfurter (currency)", "category": "currency",
     "base_url": "https://api.frankfurter.dev/v1/latest", "docs_url": "https://frankfurter.dev",
     "pricing_url": "", "auth": "none", "free_type": "FREE_WITH_FAIR_USE", "level": 1,
     "key_env": "", "card_required": "No", "commercial": "ECB reference rates",
     "free_only_verified": True, "status_note": "Registered - currency rates; later phase."},
]

BY_SLUG = {p["slug"]: p for p in REGISTRY}
# slugs that exist per category in the live router (image entries live under
# their text/shared slug where the provider is the same company)
IMAGE_SLUGS = ["svg", "pollinations", "gemini", "huggingface", "cloudflare", "ideogram"]
TEXT_SLUGS = ["local", "gemini", "groq", "openrouter", "cloudflare", "huggingface",
              "mistral", "qwen", "nvidia", "deepseek", "pollinations"]

def get(slug):
    return BY_SLUG.get(slug)
