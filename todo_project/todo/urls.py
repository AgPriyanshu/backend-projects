from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from auth.views import AuthViewSet
from core.views import TaskViewSet

router = DefaultRouter()
router.register(r"", TaskViewSet, basename=r"task")
router.register(r"auth", AuthViewSet, basename=r"auth")

urlpatterns = [path("", include(router.urls))]
