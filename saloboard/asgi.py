"""
ASGI config for saloboard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# 1. Спочатку встановлюємо налаштування
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saloboard.settings")

# 2. Ініціалізуємо Django ASGI додаток (це завантажує реєстр додатків та моделі)
django_asgi_app = get_asgi_application()

# 3. ПІСЛЯ ЦЬОГО імпортуємо те, що використовує моделі
from channels.routing import ProtocolTypeRouter, URLRouter
import salocore.routing
from salocore.middleware import JwtAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddleware(URLRouter(salocore.routing.websocket_urlpatterns)),
    }
)
