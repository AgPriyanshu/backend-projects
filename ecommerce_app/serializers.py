
from shared.serializers import BaseModelSerializer

from .models import Product


class ProductSerializer(BaseModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
