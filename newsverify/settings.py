import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-in-production")
DEBUG = os.environ.get("DEBUG", "False") == "True"
_ah = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h for h in _ah.split(",") if h] if _ah else (["*"] if DEBUG else ["localhost", "127.0.0.1", ".onrender.com"])
if not DEBUG and SECRET_KEY == "dev-only-change-me-in-production":
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SECRET_KEY must be set via environment in production (DEBUG=False).")
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "rest_framework","django_filters","corsheaders",
    "sources","news","verification","moderation","feedback_app","core","api","airouter",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SimpleRateLimitMiddleware",
]
ROOT_URLCONF = "newsverify.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","core.context_processors.stats","core.context_processors.portal_nav"]}}]
WSGI_APPLICATION = "newsverify.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
DATABASE_URL = os.environ.get("DATABASE_URL","")
if DATABASE_URL.startswith("postgres"):
    import urllib.parse as up
    u = up.urlparse(DATABASE_URL)
    _q = dict(up.parse_qsl(u.query))
    _opts = {}
    # Cloud PostgreSQL (Neon/Render) requires TLS. Honour ?sslmode= in the URL;
    # if it is absent, require SSL for every non-local host so credentials and
    # data never travel unencrypted.
    _sslmode = _q.get("sslmode") or ("require" if u.hostname not in ("localhost", "127.0.0.1") else None)
    if _sslmode: _opts["sslmode"] = _sslmode
    if _q.get("channel_binding"): _opts["channel_binding"] = _q["channel_binding"]
    DATABASES = {"default":{"ENGINE":"django.db.backends.postgresql","NAME":u.path[1:],"USER":u.username,"PASSWORD":u.password,"HOST":u.hostname,"PORT":u.port or 5432,"CONN_MAX_AGE":60,"OPTIONS":_opts}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator","OPTIONS":{"min_length":10}},
    {"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; STATICFILES_DIRS=[BASE_DIR/"static"]; STATIC_ROOT=BASE_DIR/"staticfiles"
STORAGES={"staticfiles":{"BACKEND":"whitenoise.storage.CompressedStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
REST_FRAMEWORK={"DEFAULT_PAGINATION_CLASS":"api.pagination.StandardPagination","PAGE_SIZE":20,"DEFAULT_FILTER_BACKENDS":["django_filters.rest_framework.DjangoFilterBackend","rest_framework.filters.SearchFilter","rest_framework.filters.OrderingFilter"],"DEFAULT_THROTTLE_CLASSES":["rest_framework.throttling.AnonRateThrottle"],"DEFAULT_THROTTLE_RATES":{"anon":"120/min"}}
CELERY_BROKER_URL=os.environ.get("REDIS_URL","redis://localhost:6379/0")
CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER=os.environ.get("CELERY_TASK_ALWAYS_EAGER","True")=="True"
# Token for the external free-scheduler fetch trigger (/api/fetch/trigger/).
# Empty = trigger disabled. Set the same value in Render env and in the
# scheduler's URL; never commit a real value.
FETCH_TRIGGER_TOKEN=os.environ.get("FETCH_TRIGGER_TOKEN","")
GOOGLE_FACTCHECK_API_KEY=os.environ.get("GOOGLE_FACTCHECK_API_KEY","")
GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY","")
MISTRAL_API_KEY=os.environ.get("MISTRAL_API_KEY","")
DEEPSEEK_API_KEY=os.environ.get("DEEPSEEK_API_KEY","")
QWEN_API_KEY=os.environ.get("QWEN_API_KEY","")
HF_TOKEN=os.environ.get("HF_TOKEN","")
HUGGINGFACE_API_KEY=os.environ.get("HUGGINGFACE_API_KEY","") or HF_TOKEN
POLLINATIONS_API_KEY=os.environ.get("POLLINATIONS_API_KEY","")
GROQ_API_KEY=os.environ.get("GROQ_API_KEY","")
OPENROUTER_API_KEY=os.environ.get("OPENROUTER_API_KEY","")
CLOUDFLARE_ACCOUNT_ID=os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
CLOUDFLARE_API_TOKEN=os.environ.get("CLOUDFLARE_API_TOKEN","")
NVIDIA_API_KEY=os.environ.get("NVIDIA_API_KEY","")
GUARDIAN_API_KEY=os.environ.get("GUARDIAN_API_KEY","")
GNEWS_API_KEY=os.environ.get("GNEWS_API_KEY","")
# ---- Zero-billing guard (spec 8): hard defaults, env may only tighten ----
AI_FREE_ONLY=True
ALLOW_PAID_APIS=False
IDEOGRAM_API_KEY=os.environ.get("IDEOGRAM_API_KEY","")
# ---- AI Router: daily limits are CONFIGURABLE, never hard-coded (spec 14) ----
def _ailimit(name, default):
    try: return int(os.environ.get(name, str(default)))
    except Exception: return default
AI_DAILY_LIMITS={
    "gemini_text": _ailimit("GEMINI_DAILY_LIMIT", 200),
    "mistral_text": _ailimit("MISTRAL_DAILY_LIMIT", 100),
    "qwen_text": _ailimit("QWEN_DAILY_LIMIT", 100),
    "deepseek_text": _ailimit("DEEPSEEK_DAILY_LIMIT", 100),
    "pollinations_text": _ailimit("POLLINATIONS_DAILY_LIMIT", 500),
    "pollinations_image": _ailimit("POLLINATIONS_IMAGE_DAILY_LIMIT", 500),
    "gemini_image": _ailimit("GEMINI_IMAGE_DAILY_LIMIT", 25),
    "huggingface_image": _ailimit("HUGGINGFACE_DAILY_LIMIT", 50),
    "ideogram_image": _ailimit("IDEOGRAM_DAILY_LIMIT", 0),
    "local_text": -1, "svg_image": -1,
    "groq_text": _ailimit("GROQ_DAILY_LIMIT", 500),
    "openrouter_text": _ailimit("OPENROUTER_DAILY_LIMIT", 200),
    "cloudflare_text": _ailimit("CLOUDFLARE_DAILY_LIMIT", 300),
    "cloudflare_image": _ailimit("CLOUDFLARE_IMAGE_DAILY_LIMIT", 100),
    "huggingface_text": _ailimit("HUGGINGFACE_TEXT_DAILY_LIMIT", 100),
    "nvidia_text": _ailimit("NVIDIA_DAILY_LIMIT", 100),
    "svg_text": -1,
}
# Monthly configured caps (spec 6); -1/0 = no monthly cap configured.
AI_MONTHLY_LIMITS={
    "gemini_text": _ailimit("GEMINI_MONTHLY_LIMIT", 0),
    "huggingface_text": _ailimit("HUGGINGFACE_MONTHLY_LIMIT", 500),
    "huggingface_image": _ailimit("HUGGINGFACE_IMAGE_MONTHLY_LIMIT", 500),
    "openrouter_text": _ailimit("OPENROUTER_MONTHLY_LIMIT", 1000),
}
AI_COOLDOWN_MINUTES=_ailimit("AI_COOLDOWN_MINUTES", 10)
AI_CACHE_TTL_HOURS={"text": _ailimit("AI_CACHE_TTL_TEXT_HOURS", 24), "image": _ailimit("AI_CACHE_TTL_IMAGE_HOURS", 720)}
AI_FAILURE_THRESHOLD=_ailimit("AI_FAILURE_THRESHOLD", 3)
AUTO_VERIFY_PER_SOURCE=int(os.environ.get("AUTO_VERIFY_PER_SOURCE","8"))
AUTO_COVERS_PER_SOURCE=int(os.environ.get("AUTO_COVERS_PER_SOURCE","3"))
GOOGLE_CSE_API_KEY=os.environ.get("GOOGLE_CSE_API_KEY","")
GOOGLE_CSE_ID=os.environ.get("GOOGLE_CSE_ID","")
# ---- Verification search providers (pluggable) ----
# Verification gathers evidence through a pluggable SearchProvider layer
# (verification/providers.py). The Google Fact Check Tools API is the default
# provider. Google CSE is a LEGACY, optional provider only: it is closed to
# new customers and is discontinued on 2027-01-01, so it must NEVER become a
# hard dependency. It runs only when listed in SEARCH_PROVIDERS *and*
# SEARCH_GOOGLE_CSE_ENABLED is True *and* both CSE keys are set.
SEARCH_PROVIDERS=[p.strip() for p in os.environ.get("SEARCH_PROVIDERS","factcheck").split(",") if p.strip()]
SEARCH_GOOGLE_CSE_ENABLED=os.environ.get("SEARCH_GOOGLE_CSE_ENABLED","False")=="True"
SECURE_REFERRER_POLICY="same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY="same-origin"
if not DEBUG:
    SECURE_SSL_REDIRECT=True; SESSION_COOKIE_SECURE=True; CSRF_COOKIE_SECURE=True
    SECURE_HSTS_SECONDS=31536000; SECURE_HSTS_INCLUDE_SUBDOMAINS=True; SECURE_HSTS_PRELOAD=True
LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"console":{"class":"logging.StreamHandler"}},"root":{"handlers":["console"],"level":"INFO"}}
