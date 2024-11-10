from rest_framework.serializers import Serializer

from shared.serializers import BaseModelSerializer, TimePeriodField

from .models import Expense


class ExpensesSerializer(BaseModelSerializer):
    class Meta:
        model = Expense
        fields = ("id", "title", "spend", "created_at")
        read_only_fields = ("id",)


class ExpensesQueryParams(Serializer):
    time_period = TimePeriodField(required=False)
