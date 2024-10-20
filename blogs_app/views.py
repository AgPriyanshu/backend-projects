from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Blogs
from .serializers import BlogsSerializer


# Create your views here.
class BlogsViewSet(ModelViewSet):
    queryset = Blogs.objects.all()
    serializer_class = BlogsSerializer
