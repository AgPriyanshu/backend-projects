from django.urls import include, path
from rest_framework.routers import DefaultRouter

from device_classifier.views import DeviceClassifierViewSet

router = DefaultRouter()
router.register(r'', DeviceClassifierViewSet, basename='classify')

urlpatterns = [
    path('', include(router.urls)),
]
