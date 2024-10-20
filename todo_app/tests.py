from django.test import TestCase, Client
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.authtoken.models import Token
from .models import Task
from django.contrib.auth.models import User


class TestTasks(TestCase):
    def setUp(self):
        self.task1 = Task.objects.create(description="Description1")
        self.task2 = Task.objects.create(description="Description2")
        self.task1.save()
        self.task2.save()

        user_creds = {"username": "test-suite@gmail.com", "password": "test-password"}
        self.test_user = User.objects.create_user(**user_creds)
        self.user_token = Token.objects.get_or_create(user=self.test_user)
        self.client = Client(
            headers={"Authorization": "Bearer " + self.user_token[0].key}
        )

    def test_can_create_task(self):
        # Arrange.
        task = {"description": "Description3"}
        url = reverse("task-list")

        # Act.
        response = self.client.post(url, data=task)
        response_data = response.json()["data"]

        # Assert.
        self.assertEqual(response_data["description"], task["description"])

    def test_can_get_task_list(self):
        # Arrange.
        url = reverse("task-list")

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(len(response.data), 2)

    def test_can_get_task_detail(self):
        # Arrange.
        url = reverse("task-detail", kwargs={"pk": str(self.task1.id)})

        # Act.
        response = self.client.get(url)
        response_data = response.json()["data"]

        # Assert.
        self.assertEqual(response_data["id"], str(self.task1.id))

    def test_can_delete_task(self):
        # Arrange.
        url = reverse("task-detail", kwargs={"pk": str(self.task1.id)})

        # Act.
        response = self.client.delete(url)

        # Assert.
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
