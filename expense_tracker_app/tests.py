from rest_framework.reverse import reverse
from rest_framework.status import HTTP_204_NO_CONTENT

from shared.tests import BaseTest

from .models import Expense


class TestExpenses(BaseTest):
    def setUp(self):
        self.authenticate(self.test_user)
        self.expense1 = Expense.objects.create(title="Groceries", spend=1000)
        self.expense2 = Expense.objects.create(title="TV", spend=10000)

    def test_can_list_expenses(self):
        # Arrange.
        url = reverse("expenses-list")
        expense1_assertion_obj = {
            "title": "Groceries",
            "spend": "1000.00",
        }
        expense2_assertion_obj = {
            "title": "TV",
            "spend": "10000.00",
        }

        # Act.
        response = self.client.get(url)
        response_json = response.json()["data"]

        # Assert.
        self.assertDictEqual(
            {"title": response_json[0]["title"], "spend": response_json[0]["spend"]},
            expense1_assertion_obj,
        )
        self.assertDictEqual(
            {"title": response_json[1]["title"], "spend": response_json[1]["spend"]},
            expense2_assertion_obj,
        )

    def test_can_add_expense(self):
        # Arrange.
        url = reverse("expenses-list")
        expense = {
            "title": "Groceries",
            "spend": "1000.00",
        }

        # Act.
        response = self.client.post(url, data=expense)
        response_json = response.json()["data"]
        expenseObj = Expense.objects.filter(id=response_json["id"]).first()

        # Assert.
        self.assertEqual(expenseObj.title, expense["title"])

    def test_can_fetch_expense(self):
        # Arrange.
        id = self.expense1.id
        url = reverse("expenses-detail", kwargs={"pk": id})

        # Act.
        response = self.client.get(url).json()

        # Assert.
        self.assertEqual(str(id), response["data"]["id"])
        self.assertEqual(self.expense1.title, response["data"]["title"])

    def test_can_update_expense(self):
        # Arrange.
        id = self.expense1.id
        url = reverse("expenses-detail", kwargs={"pk": id})

        # Act.
        response = self.client.patch(url, data={"title": "Updated Groceries"}).json()
        response_data = response["data"]

        # Assert.
        self.assertEqual(str(id), response_data["id"])
        self.assertEqual("Updated Groceries", response_data["title"])

    def test_can_delete_expense(self):
        # Arrange.
        expense_to_delete = Expense.objects.create(title="Groceries", spend=1000)
        url = reverse("expenses-detail", kwargs={"pk": expense_to_delete.id})

        # Act.
        response = self.client.delete(url)

        # Assert.
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
