import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saloboard.settings")

app = Celery("saloboard")

# Берём конфигурацию из django.conf.settings, ключи с префиксом CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически обнаруживаем tasks.py во всех INSTALLED_APPS
app.autodiscover_tasks()
