from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartsViewSet, CategoriesViewSet, ProductsViewSet

router = DefaultRouter()
router.register(r"products", ProductsViewSet, basename="products")
router.register(r"categories", CategoriesViewSet, basename="categories")
router.register(r"carts", CartsViewSet, basename="carts")

urlpatterns = [path("", include(router.urls))]
