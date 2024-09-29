from rest_framework.serializers import ModelSerializer
from .models import Blogs

class BlogsSerializer(ModelSerializer):
  class Meta:
    model = Blogs
    fields = '__all__'