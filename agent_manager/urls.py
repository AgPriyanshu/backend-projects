from django.urls import include, path
from rest_framework.routers import DefaultRouter

from agent_manager.views import ChatSessionViewSet, LLMViewSet

router = DefaultRouter()
router.register(r"chat-sessions", ChatSessionViewSet, basename="agent-chat-sessions")
router.register(r"llms", LLMViewSet, basename="llms")

urlpatterns = [path("", include(router.urls))]
