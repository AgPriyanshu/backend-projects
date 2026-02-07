from django.urls import include, path
from rest_framework.routers import DefaultRouter

from web_gis_app.views.layer_views import LayerViewSet

from .views.dataset_views import DatasetNodeViewSet

router = DefaultRouter()

router.register(r"datasets", DatasetNodeViewSet, basename="datasets")
router.register(r"layers", LayerViewSet, basename="layers")

urlpatterns = [path("", include(router.urls))]
