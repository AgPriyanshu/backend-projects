from shared.serializers import BaseSerializer

from .models import Expense


class ExpensesSerializer(BaseSerializer):
    class Meta:
        model = Expense
        fields = ("id", "title", "spend")
        read_only_fields = ("id",)
