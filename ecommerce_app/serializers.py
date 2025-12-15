from django.conf import settings
from moneyed import Money
from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from .models import Cart, CartItem, Category, Product


class MoneyFieldSerializer(serializers.Field):
    def to_representation(self, value):
        if isinstance(value, Money):
            return {
                "amount": str(value.amount),
                "currency": str(value.currency),
            }
        if value is None:
            return None
        try:
            return {
                "amount": str(value),
                "currency": getattr(value, "currency", settings.DEFAULT_CURRENCY),
            }
        except Exception as e:
            return {"error": str(e)}

    def to_internal_value(self, data):
        try:
            return Money(data, settings.DEFAULT_CURRENCY)
        except Exception:
            raise serializers.ValidationError("Invalid money input")


class ProductSerializer(BaseModelSerializer):
    price = MoneyFieldSerializer(required=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "category",
            "quantity",
            "price",
        )
        read_only_fields = (
            "id",
            "added_by",
        )


class CategorySerializer(BaseModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class CartSerializer(BaseModelSerializer):
    class Meta:
        model = Cart
        fields = "__all__"


class CartItemSerializer(BaseModelSerializer):
    class Meta:
        model = CartItem
        fields = "__all__"

    def to_representation(self, instance):
        response = {
            "product_id": instance.product.id,
            "product_name": instance.product.name,
            "quantity": instance.quantity,
        }

        return response
