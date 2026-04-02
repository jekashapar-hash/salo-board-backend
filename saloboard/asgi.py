"""
ASGI config for saloboard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from salocore.middleware import JwtAuthMiddleware
import salocore.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saloboard.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware(
        URLRouter(salocore.routing.websocket_urlpatterns)
    ),
})
