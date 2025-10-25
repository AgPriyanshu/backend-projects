from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductsViewSet

router = DefaultRouter()
router.register(r"products", ProductsViewSet, basename="products")

urlpatterns = [path("", include(router.urls))]
