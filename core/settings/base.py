import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IS_TESTING = "test" in sys.argv


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() == "true"


def env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def env_list(name):
    return [
        item.strip() for item in os.environ.get(name, "").split(",") if item.strip()
    ]


def database_config(ssl_require=False):
    if os.getenv("DATABASE_URL"):
        return {
            "default": dj_database_url.config(
                default=os.getenv("DATABASE_URL"),
                conn_max_age=600,
                ssl_require=ssl_require,
            )
        }

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "default_db_name"),
            "USER": os.environ.get("DB_USER", "default_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "default_password"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }


SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "development-only-fallback-secret-key-change-in-railway-env-2026",
)

DEBUG = env_bool("DEBUG", False)

SITE_NAME = "Sponsorship Database"
BASE_DOMAIN = "sponsorwithpendeza.org"
SITE_URL = os.environ.get("SITE_URL", f"https://{BASE_DOMAIN}")

RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
ALLOWED_HOSTS = [BASE_DOMAIN, ".up.railway.app"]
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
ALLOWED_HOSTS.extend(env_list("ALLOWED_HOSTS"))

CSRF_TRUSTED_ORIGINS = ["https://sponsorwithpendeza.org"]
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
CSRF_TRUSTED_ORIGINS.extend(env_list("CSRF_TRUSTED_ORIGINS"))

CORS_ALLOWED_ORIGINS = [SITE_URL]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "social_django",
    "bootstrap5",
    "formtools",
    "crispy_forms",
    "crispy_bootstrap5",
    "django.contrib.humanize",
    "django_select2",
    "cloudinary",
    "rest_framework",
    "apps.users",
    "apps.child",
    "apps.staff",
    "apps.sponsor",
    "apps.finance",
    "apps.sponsorship",
    "apps.client",
    "apps.reports",
    "apps.dashboard",
    "apps.loans",
    "apps.savings",
    "apps.inventory.customers",
    "apps.inventory.supplier",
    "apps.inventory.products",
    "apps.inventory.sales",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR, BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "apps.users.context_processors.guest_profiles_context",
                "apps.users.context_processors.guest_user_feedback_context",
                "apps.users.context_processors.low_stock_alerts_context",
                "apps.loans.context_processors.loan_dashboard_context",
                "apps.savings.context_processors.savings_notifications_context",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = database_config(ssl_require=env_bool("DATABASE_SSL_REQUIRE", False))

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = (
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = BASE_DIR / "media"
LOCAL_MEDIA_URL = "/media/"

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if IS_TESTING
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
}

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "login"

SOCIAL_AUTH_GITHUB_KEY = str(os.getenv("GITHUB_KEY"))
SOCIAL_AUTH_GITHUB_SECRET = str(os.getenv("GITHUB_SECRET"))
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = str(os.getenv("GOOGLE_KEY"))
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = str(os.getenv("GOOGLE_SECRET"))
SOCIAL_AUTH_REQUESTS_TIMEOUT = env_float("SOCIAL_AUTH_REQUESTS_TIMEOUT", 10)
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "apps.users.pipeline.require_google_login_token",
)

# Redis / Celery
# Prefer explicit Celery variables when set, otherwise fall back to REDIS_URL.
# This makes Railway deployments easier because web and worker services can use
# either REDIS_URL, CELERY_BROKER_URL, or CELERY_RESULT_BACKEND.
REDIS_URL = os.environ.get("REDIS_URL")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL") or REDIS_URL
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND") or REDIS_URL

if not CELERY_BROKER_URL:
    raise Exception("CELERY_BROKER_URL or REDIS_URL is not set!")

if not CELERY_RESULT_BACKEND:
    raise Exception("CELERY_RESULT_BACKEND or REDIS_URL is not set!")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Nairobi"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = os.getenv("RESEND_API_URL", "https://api.resend.com/emails")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    RESEND_FROM_EMAIL or EMAIL_HOST_USER,
)
if not RESEND_FROM_EMAIL:
    RESEND_FROM_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    (
        "core.email_backends.ResendEmailBackend"
        if RESEND_API_KEY
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)

BOO_EMAIL = os.getenv("BOO_EMAIL", "")
HOF_EMAIL = os.getenv("HOF_EMAIL", "")
ED_EMAIL = os.getenv("ED_EMAIL", "")
ACCOUNTANT_EMAIL = os.getenv("ACCOUNTANT_EMAIL", "")
PROGS_ADMIN_EMAIL = os.getenv("PROGS_ADMIN_EMAIL", "")

SESSION_COOKIE_AGE = 7200
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": os.environ.get("DJANGO_LOG_LEVEL", "DEBUG"),
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": os.environ.get("DJANGO_LOG_LEVEL", "DEBUG"),
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "DEBUG"),
            "propagate": True,
        },
        "celery.utils.functional": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv("FLUTTERWAVE_ENCRYPTION_KEY")

SUBSCRIPTION_KEY = os.getenv("SUBSCRIPTION_KEY")
MOMO_API_USER = os.getenv("MOMO_API_USER")
MOMO_API_KEY = os.getenv("MOMO_API_KEY")
MOMO_CALLBACK_URL = os.getenv(
    "MOMO_CALLBACK_URL",
    default="https://sponsorwithpendeza.org/sponsorship/mtn-pay/callback/",
)
