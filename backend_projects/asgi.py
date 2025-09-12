"""
ASGI config for backend_projects project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_projects.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import routing after Django initialization
import ai_chat.routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            AuthMiddlewareStack(URLRouter(ai_chat.routing.websocket_urlpatterns)),
            (
                ["*"]
                if os.environ.get("DEBUG", "0") == "1"
                else [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "https://yourdomain.com",
                ]
            ),
        ),
    }
)
