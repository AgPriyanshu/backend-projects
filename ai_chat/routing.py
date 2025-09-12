from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # WebSocket URL for individual chat sessions
    path('ws/ai-chat/session/<uuid:session_id>/', consumers.ChatConsumer.as_asgi()),
    
    # WebSocket URL for chat list updates
    path('ws/ai-chat/sessions/', consumers.ChatListConsumer.as_asgi()),
] 