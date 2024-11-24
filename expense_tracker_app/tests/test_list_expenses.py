from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework.reverse import reverse

from shared.tests import BaseTest

from ..models import Expense
from ..serializers import ExpensesSerializer


class TestExpenses(BaseTest):
    def setUp(self):
        self.authenticate(self.test_user)
        self.expense1 = Expense.objects.create(title="Groceries", spend=1000)
        self.expense2 = Expense.objects.create(title="TV", spend=10000)

    def test_can_list_expenses(self):
        # Arrange.
        url = reverse("expenses-list")
        expected_results = ExpensesSerializer(
            [self.expense1, self.expense2], many=True
        ).data

        # Act.
        response = self.client.get(url)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)

    def test_can_list_expenses_from_last_week(self):
        # Arrange.
        today = timezone.now()
        self.expense1.created_at = today - relativedelta(weeks=1)
        self.expense1.save()
        self.expense2.created_at = today - relativedelta(months=1)
        self.expense2.save()
        expected_results = ExpensesSerializer([self.expense1], many=True).data

        url = reverse("expenses-list")
        query_params = {"time_period": "last_week"}

        # Act.
        response = self.client.get(url, query_params)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)

    def test_can_list_expenses_from_last_month(self):
        # Arrange.
        today = timezone.now()
        self.expense1.created_at = today - relativedelta(weeks=1)
        self.expense1.save()
        self.expense2.created_at = today - relativedelta(months=1)
        self.expense2.save()
        expense3 = Expense.objects.create(
            title="Falana", spend=10000, created_at=today - relativedelta(months=2)
        )
        expected_results = ExpensesSerializer(
            [self.expense1, self.expense2], many=True
        ).data

        url = reverse("expenses-list")
        query_params = {"time_period": "last_month"}

        # Act.
        response = self.client.get(url, query_params)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)
