from django.test import TestCase, Client
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK
from django.contrib.auth.models import User

user_creds = {"username": "test-suite@gmail.com", "password": "test-password"}


class TestTasks(TestCase):
    def setUp(self):
        self.test_user = User.objects.create_user(**user_creds)
        self.client = Client()

    def test_can_user_register(self):
        # Arrange.
        test_user_creds = {
            "username": "test-suite+1@gmail.com",
            "password": "test-password",
        }

        # Act.
        url = reverse("auth-register")
        response = self.client.post(
            url, data=test_user_creds, content_type="application/json"
        )

        # Assert.
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_can_user_login(self):
        # Act.
        url = reverse("auth-login")
        response = self.client.post(
            url,
            data={
                "username": self.test_user.username,
                "password": "test-password",
            },
            content_type="application/json",
        )
        response_body = response.json()["data"]

        # Assert.
        self.assertIn("token", response_body)
