from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotesViewSet

router = DefaultRouter()
router.register(r"", NotesViewSet, basename="expenses")

urlpatterns = [path("", include(router.urls))]
