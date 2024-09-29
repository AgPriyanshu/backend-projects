import uuid
from django.db import models

# Create your models here.
class Blogs(models.Model):
  id = models.UUIDField(primary_key=True,default=uuid.uuid4)
  title = models.CharField(max_length=200)
  author = models.CharField(max_length=50)
  content = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)