from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import BlogsViewSet


router = DefaultRouter()
router.register(r"blogs", BlogsViewSet, basename="blog")

urlpatterns = [path("", include(router.urls))]
