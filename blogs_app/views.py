from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Blog
from .serializers import BlogsSerializer


# Create your views here.
class BlogsViewSet(ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogsSerializer
    permission_classes = (IsAuthenticated,)
