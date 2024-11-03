from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase


class BaseTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        credentials = {"username": "test-suite@gmail.com", "password": "test-password"}
        cls.test_user = User.objects.create_user(**credentials)
        cls.client = APIClient()

    def authenticate(self, user=None):
        self.user_token = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.user_token[0].key)
