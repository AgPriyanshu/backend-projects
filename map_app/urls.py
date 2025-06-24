from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "map_app"

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r"layers", views.LayerViewSet, basename="layer")
router.register(r"features", views.FeatureViewSet, basename="feature")
router.register(r"attributes", views.FeatureAttributeViewSet, basename="attribute")

urlpatterns = [
    # Direct API endpoints using router
    path("", include(router.urls)),
]
