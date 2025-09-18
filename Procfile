release: python manage.py migrate
web: gunicorn core.wsgi --timeout 120 --workers 2 --threads 4 --log-level debug