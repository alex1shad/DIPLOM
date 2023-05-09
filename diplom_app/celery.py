import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diplom_app.settings')

app = Celery('diplom_app')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks()
