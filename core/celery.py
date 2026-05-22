import os

from celery import Celery
from dotenv import load_dotenv

from core.settings import get_settings_module

load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    get_settings_module(os.environ.get("DJANGO_ENV")),
)

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
