from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.notification_views import NotificationViewSet
from .views.sse_views import sse_view

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("events/", sse_view, name="sse-events"),
] + router.urls
