from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartsViewSet, CategoriesViewSet, ProductsViewSet

router = DefaultRouter()
router.register("products", ProductsViewSet, basename="products")
router.register("categories", CategoriesViewSet, basename="categories")
router.register("carts", CartsViewSet, basename="carts")

urlpatterns = [path("", include(router.urls))]
