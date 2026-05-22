import os

from .base import *  # noqa: F403

DEBUG = False
SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI = os.environ.get(
    "SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI",
    "https://sponsorwithpendeza.org/oauth/complete/google-oauth2/",
)

DATABASES = database_config(  # noqa: F405
    ssl_require=env_bool("DATABASE_SSL_REQUIRE", True)  # noqa: F405
)

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)  # noqa: F405
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(  # noqa: F405
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)  # noqa: F405
