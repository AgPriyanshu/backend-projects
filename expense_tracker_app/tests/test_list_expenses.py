from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework.reverse import reverse

from shared.tests import BaseTest

from ..models import Expense
from ..serializers import ExpensesSerializer


class TestExpenses(BaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        today = timezone.now()
        cls.expense1 = Expense.objects.create(title="Groceries", spend=1000)
        cls.expense2 = Expense.objects.create(title="TV", spend=10000)
        # Last Week.
        cls.expense_last_week = Expense.objects.create(title="Playstation", spend=50000)
        cls.expense_last_week.created_at = today + relativedelta(weeks=-1)
        cls.expense_last_week.save()

        # Last Month.
        cls.expense_last_month = Expense.objects.create(title="Furniture", spend=100000)
        cls.expense_last_month.created_at = today + relativedelta(months=-1)
        cls.expense_last_month.save()

        # 2 Months Old.
        cls.expense_2_months_old = Expense.objects.create(title="Flat", spend=1000000)
        cls.expense_2_months_old.created_at = today + relativedelta(months=-2)
        cls.expense_2_months_old.save()

    def setUp(self):
        self.authenticate(self.test_user)

    def test_can_list_expenses(self):
        # Arrange.
        url = reverse("expenses-list")
        expected_results = ExpensesSerializer(
            [
                self.expense1,
                self.expense2,
                self.expense_last_week,
                self.expense_last_month,
                self.expense_2_months_old,
            ],
            many=True,
        ).data

        # Act.
        response = self.client.get(url)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)

    def test_can_list_expenses_from_last_week(self):
        # Arrange.
        expected_results = ExpensesSerializer(
            [
                self.expense1,
                self.expense2,
                self.expense_last_week,
            ],
            many=True,
        ).data

        url = reverse("expenses-list")
        query_params = {"time_period": "last_week"}

        # Act.
        response = self.client.get(url, query_params)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)

    def test_can_list_expenses_from_last_month(self):
        # Arrange.
        expected_results = ExpensesSerializer(
            [
                self.expense1,
                self.expense2,
                self.expense_last_week,
                self.expense_last_month,
            ],
            many=True,
        ).data

        url = reverse("expenses-list")
        query_params = {"time_period": "last_month"}

        # Act.
        response = self.client.get(url, query_params)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)

    def test_can_list_expenses_absolute_date(self):
        # Arrange.
        today = timezone.now()
        last_year = today + relativedelta(years=-1)
        last_month = today + relativedelta(months=-1)
        expected_results = ExpensesSerializer(
            [
                self.expense_last_month,
                self.expense_2_months_old,
            ],
            many=True,
        ).data

        url = reverse("expenses-list")
        query_params = {
            "time_period": f"{last_year.strftime('%d-%m-%Y')},{last_month.strftime('%d-%m-%Y')}"
        }

        # Act.
        response = self.client.get(url, query_params)
        response_json = response.json()["data"]

        # Assert.
        self.assertCountEqual(response_json, expected_results)
