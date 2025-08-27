release: python manage.py migrate
web: gunicorn core.wsgi --timeout 60 --workers 3 --threads 2


