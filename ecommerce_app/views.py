from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class ProductsViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        return super().get_queryset()

    def get_permissions(self):
        if self.request.method == "POST":
            self.permission_classes = [IsAdminUser]
        elif self.request.method == "GET":
            self.permission_classes = [IsAuthenticatedOrReadOnly]

        return super().get_permissions()

    def perform_create(self, serializer):
        """Automatically assign the logged-in user to the user field."""
        serializer.save(added_by=self.request.user)

    @method_decorator(cache_page(60 * 60 * 24))  # sec * min * hours = 1 day.
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CategoriesViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            self.permission_classes = [IsAdminUser]
        elif self.request.method == "GET":
            self.permission_classes = [IsAuthenticatedOrReadOnly]

        return super().get_permissions()
