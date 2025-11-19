from django.conf import settings
from moneyed import Money
from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from .models import Category, Product


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
            "name",
            "category",
            "quantity",
            "price",
        )
        read_only_fields = ("added_by",)


class CategorySerializer(BaseModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
