import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-in-production")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "rest_framework","django_filters","corsheaders",
    "sources","news","verification","moderation","feedback_app","core","api",
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
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","core.context_processors.stats"]}}]
WSGI_APPLICATION = "newsverify.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
DATABASE_URL = os.environ.get("DATABASE_URL","")
if DATABASE_URL.startswith("postgres"):
    import urllib.parse as up
    u = up.urlparse(DATABASE_URL)
    DATABASES = {"default":{"ENGINE":"django.db.backends.postgresql","NAME":u.path[1:],"USER":u.username,"PASSWORD":u.password,"HOST":u.hostname,"PORT":u.port or 5432}}
AUTH_PASSWORD_VALIDATORS = [{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"}]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; STATICFILES_DIRS=[BASE_DIR/"static"]; STATIC_ROOT=BASE_DIR/"staticfiles"
STORAGES={"staticfiles":{"BACKEND":"whitenoise.storage.CompressedStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
REST_FRAMEWORK={"DEFAULT_PAGINATION_CLASS":"rest_framework.pagination.PageNumberPagination","PAGE_SIZE":20,"DEFAULT_FILTER_BACKENDS":["django_filters.rest_framework.DjangoFilterBackend","rest_framework.filters.SearchFilter","rest_framework.filters.OrderingFilter"],"DEFAULT_THROTTLE_CLASSES":["rest_framework.throttling.AnonRateThrottle"],"DEFAULT_THROTTLE_RATES":{"anon":"120/min"}}
CELERY_BROKER_URL=os.environ.get("REDIS_URL","redis://localhost:6379/0")
CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER=os.environ.get("CELERY_TASK_ALWAYS_EAGER","True")=="True"
GOOGLE_FACTCHECK_API_KEY=os.environ.get("GOOGLE_FACTCHECK_API_KEY","")
GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY","")
AUTO_VERIFY_PER_SOURCE=int(os.environ.get("AUTO_VERIFY_PER_SOURCE","8"))
GOOGLE_CSE_API_KEY=os.environ.get("GOOGLE_CSE_API_KEY","")
GOOGLE_CSE_ID=os.environ.get("GOOGLE_CSE_ID","")
if not DEBUG:
    SECURE_SSL_REDIRECT=True; SESSION_COOKIE_SECURE=True; CSRF_COOKIE_SECURE=True
    SECURE_HSTS_SECONDS=31536000; SECURE_HSTS_INCLUDE_SUBDOMAINS=True; SECURE_HSTS_PRELOAD=True
LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"console":{"class":"logging.StreamHandler"}},"root":{"handlers":["console"],"level":"INFO"}}
