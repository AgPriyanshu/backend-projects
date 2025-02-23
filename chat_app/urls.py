from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatRoomsViewSet, MessagesViewSet

router = DefaultRouter()
router.register(r"messages", MessagesViewSet, basename="chat-messages")
router.register(r"rooms", ChatRoomsViewSet, basename="chat-rooms")

urlpatterns = [path("", include(router.urls))]
