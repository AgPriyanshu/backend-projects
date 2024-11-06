from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Expense
from .serializers import ExpensesSerializer


class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpensesSerializer
    permission_classes = [IsAuthenticated]
