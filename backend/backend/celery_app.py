from __future__ import annotations
import os
from celery import Celery
from django.conf import settings



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
# set timezone safely from environment variable (avoid importing settings at top-level)
app.conf.timezone = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kathmandu")


# For debugging
@app.task(bind=True)
def debug_task(self):
    return f'Request: {self.request!r}'
