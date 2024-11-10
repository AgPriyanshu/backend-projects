from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from shared.serializers.constants import RecentTimePeriod

from .models import Expense
from .serializers import ExpensesQueryParams, ExpensesSerializer


class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpensesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_set = super().get_queryset()
        if len(self.request.query_params) > 0:
            serializer = ExpensesQueryParams(data=self.request.query_params)
            serializer.is_valid(raise_exception=True)

            time_period = serializer.validated_data["time_period"]
            if isinstance(time_period, RecentTimePeriod):
                if date_range := RecentTimePeriod.get_date_range(
                    RecentTimePeriod.get_enum(time_period)
                ):
                    return query_set.filter(created_at__date__range=date_range)
            elif isinstance(time_period, tuple):
                return query_set.filter(created_at__date__range=time_period)

        return super().get_queryset()
