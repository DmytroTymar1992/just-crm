#just_crm/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'just_crm.settings')  # Замініть myproject на ім'я вашого проекту

app = Celery('just_crm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
