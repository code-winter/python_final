import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diplom_site.settings")
app = Celery("diplom_site")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
