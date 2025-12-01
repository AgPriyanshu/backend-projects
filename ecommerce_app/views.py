
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shared.views import BaseModelViewSet

from .models import Cart, CartItem, Category, Product
from .serializers import CartItemSerializer, CategorySerializer, ProductSerializer


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


class CartsViewSet(BaseModelViewSet):
    queryset = Cart.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = CartItemSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()
        # import pdb

        # pdb.set_trace()

        if len(queryset) == 0:
            cart = Cart.objects.create(user=request.user)
            cart_items = serializer.validated_data
            cart_item = CartItem(**cart_items[0])
            cart_item.save()
            cart.items.add(cart_item)
            cart.save()
        else:
            cart = queryset[0]

        response = {
            "message": "Products added to cart successfully",
            "data": {
                "id": cart.id,
                "items": (
                    cart.items.all().values(
                        "id",
                        "quantity",
                        "product",
                    )
                ),
                "count": cart.count,
            },
        }

        return Response(response)
