from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BlogsViewSet

router = DefaultRouter()
router.register(r"", BlogsViewSet, basename="blogs")

urlpatterns = [path("", include(router.urls))]
