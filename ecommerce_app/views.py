from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet

from .models import Product
from .serializers import ProductSerializer


class ProductsViewSet(ModelViewSet):
    queryset = Product.objects.all()
    permission_classes = [IsAdminUser]
    serializer_class = ProductSerializer
