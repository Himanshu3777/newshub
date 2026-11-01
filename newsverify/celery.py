import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE","newsverify.settings")
app=Celery("newsverify"); app.config_from_object("django.conf:settings",namespace="CELERY"); app.autodiscover_tasks()
app.conf.beat_schedule={"fetch-news-hourly":{"task":"news.tasks.fetch_all_sources_task","schedule":3600.0}}
