"""
ASGI config for saloboard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os  # noqa: I001
from django.core.asgi import get_asgi_application

# 1. Спочатку встановлюємо налаштування
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saloboard.settings")

# 2. Ініціалізуємо Django ASGI додаток (це завантажує реєстр додатків та моделі)
django_asgi_app = get_asgi_application()

# 3. ПІСЛЯ ЦЬОГО імпортуємо те, що використовує моделі
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402, I001
import salocore.routing  # noqa: E402
from salocore.middleware import JwtAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddleware(URLRouter(salocore.routing.websocket_urlpatterns)),
    }
)