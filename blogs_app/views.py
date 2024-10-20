from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Blog
from .serializers import BlogsSerializer


# Create your views here.
class BlogsViewSet(ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogsSerializer
