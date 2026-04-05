"""
ASGI config for backend_projects project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_projects.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from agent_manager.middleware import BearerTokenAuthMiddleware  # noqa: E402
from agent_manager.routing import (  # noqa: E402
    websocket_urlpatterns as agent_manager_websocket_urlpatterns,
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            BearerTokenAuthMiddleware(
                URLRouter(agent_manager_websocket_urlpatterns)
            )
        ),
    }
)
