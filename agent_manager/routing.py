from django.urls import path

from agent_manager.consumers import ChatConsumer

websocket_urlpatterns = [
    path(
        "ws/ai/sessions/<uuid:session_id>/",
        ChatConsumer.as_asgi(),  # type: ignore
    ),
]
