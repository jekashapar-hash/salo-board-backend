# Загружаем Celery-приложение при старте Django,
# чтобы @shared_task и periodic tasks работали корректно.
from .celery import app as celery_app

__all__ = ("celery_app",)
