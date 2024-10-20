from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from .views import current as current_view

router = DefaultRouter()

urlpatterns = [
    re_path(
        r"^current/(?P<location>[^/]+)",
        current_view,
    ),
]
