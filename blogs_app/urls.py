from django.urls import include, path
from .views import BlogsViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"", BlogsViewSet, basename="blogs")

urlpatterns = [path("", include(router.urls))]
