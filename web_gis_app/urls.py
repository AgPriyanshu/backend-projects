from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DatasetNodeViewSet

router = DefaultRouter()

router.register(r"datasets", DatasetNodeViewSet, basename="datasets")

urlpatterns = [path("", include(router.urls))]
