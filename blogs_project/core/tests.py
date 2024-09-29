from django.test import TestCase,Client
from core.models import Blogs
from rest_framework.reverse import reverse

# Create your tests here.
class TestBlogs(TestCase):
  def setUp(self):
    self.blog1 = Blogs.objects.create(title="Blog1")
    self.blog2 = Blogs.objects.create(title="Blog2")
    self.client = Client()

  def test_can_view_blogs(self):
    # Act.
    url = reverse('blog-list')
    response = self.client.get(url)
    response_json = response.json()['data']

    # Assert.
    self.assertEqual(response_json[0]['title'],self.blog1.title)
    self.assertEqual(response_json[1]['title'],self.blog2.title)

  def test_can_update_blogs(self):
    # Arrange.
    blog_test = Blogs.objects.create(title="BlogToUpdate")
    blog_test.save()

    # Act.
    url = reverse('blog-detail',kwargs={'pk': blog_test.id})
    self.client.patch(url,data={ 'title': 'BlogUpdated'},content_type='application/json')    
    blog_test_updated = Blogs.objects.get(id=blog_test.id)

    # Assert.
    self.assertEqual(blog_test_updated.title, 'BlogUpdated')

