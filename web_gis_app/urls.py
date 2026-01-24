from rest_framework.routers import DefaultRouter

from .views import DatasetNodeViewSet

router = DefaultRouter()

router.register(r"datasets/nodes", DatasetNodeViewSet, basename="dataset-node")

urlpatterns = router.urls
