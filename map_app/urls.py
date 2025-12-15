from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GeospatialImageViewSet, ObjectDetectionViewSet

router = DefaultRouter()
router.register(r'images', GeospatialImageViewSet, basename='geospatial-image')
router.register(r'detections', ObjectDetectionViewSet, basename='object-detection')

app_name = 'map_app'

urlpatterns = [
    path('api/map/', include(router.urls)),
]
