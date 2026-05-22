import os

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

from core.settings import get_settings_module

load_dotenv()


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    get_settings_module(os.environ.get("DJANGO_ENV")),
)


application = get_wsgi_application()
