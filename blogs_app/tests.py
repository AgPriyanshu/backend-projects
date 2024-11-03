from django.test import TestCase, Client
from .models import Blog
from rest_framework.reverse import reverse


class TestBlogs(TestCase):
    def setUp(self):
        self.blog1 = Blog.objects.create(title="Blog1")
        self.blog2 = Blog.objects.create(title="Blog2")
        self.client = Client()

    def test_can_view_blogs(self):
        # Act.
        url = reverse("blogs-list")
        response = self.client.get(url)
        response_json = response.json()["data"]

        # Assert.
        self.assertEqual(response_json[0]["title"], self.blog1.title)
        self.assertEqual(response_json[1]["title"], self.blog2.title)

    def test_can_update_blogs(self):
        # Arrange.
        blog_test = Blog.objects.create(title="BlogToUpdate")
        blog_test.save()

        # Act.
        url = reverse("blogs-detail", kwargs={"pk": blog_test.id})
        self.client.patch(
            url, data={"title": "BlogUpdated"}, content_type="application/json"
        )
        blog_test_updated = Blog.objects.get(id=blog_test.id)

        # Assert.
        self.assertEqual(blog_test_updated.title, "BlogUpdated")
