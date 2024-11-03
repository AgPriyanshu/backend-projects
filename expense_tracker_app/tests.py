from rest_framework.reverse import reverse

from shared.tests import BaseTest

from .models import Expense


class TestExpenses(BaseTest):
    def setUp(self):
        self.authenticate(self.test_user)
        self.expense1 = Expense.objects.create(title="Groceries", spend=1000)
        self.expense2 = Expense.objects.create(title="TV", spend=10000)

    def test_can_list_blogs(self):
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

    # def test_can_update_blogs(self):
    #     # Arrange.
    #     blog_test = Blog.objects.create(title="BlogToUpdate")
    #     blog_test.save()

    #     # Act.
    #     url = reverse("blogs-detail", kwargs={"pk": blog_test.id})
    #     self.client.patch(
    #         url, data={"title": "BlogUpdated"}, content_type="application/json"
    #     )
    #     blog_test_updated = Blog.objects.get(id=blog_test.id)

    #     # Assert.
    #     self.assertEqual(blog_test_updated.title, "BlogUpdated")
