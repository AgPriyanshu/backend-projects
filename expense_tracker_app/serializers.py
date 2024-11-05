from rest_framework.serializers import ModelSerializer

from .models import Expense


class ExpensesSerializer(ModelSerializer):
    class Meta:
        model = Expense
        fields = ("id", "title", "spend")
        read_only_fields = ("id",)
