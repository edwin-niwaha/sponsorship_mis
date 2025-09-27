web: python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers=2 --timeout=60
worker: celery -A core worker --loglevel=info --concurrency=2 -Q celery