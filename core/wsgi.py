"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

# import os

# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# application = get_wsgi_application()

import os

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

load_dotenv()


if os.environ.get("DJANGO_ENV") == "development":
    settings = "core.settings_dev"
else:
    settings = "core.settings"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings)


application = get_wsgi_application()
