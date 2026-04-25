from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CharacterViewSet, StatViewSet

router = DefaultRouter()
router.register(r"characters", CharacterViewSet, basename="characters")
router.register(r"stats", StatViewSet, basename="stats")

urlpatterns = [path("", include(router.urls))]
