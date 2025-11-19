from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoriesViewSet, ProductsViewSet

router = DefaultRouter()
router.register(r"products", ProductsViewSet, basename="products")
router.register(r"categories", CategoriesViewSet, basename="categories")

urlpatterns = [path("", include(router.urls))]
