web: gunicorn newsverify.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4
worker: celery -A newsverify worker -l info
beat: celery -A newsverify beat -l info
