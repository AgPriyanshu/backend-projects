from rest_framework.routers import DefaultRouter

from .views import DatasetViewSet

router = DefaultRouter()

router.register(r"datasets", DatasetViewSet, basename="datasets")
