from django.urls import include, path
from rest_framework.routers import DefaultRouter

from backend_projects.settings import BASE_DIR
from .views import ExpenseViewSet

router = DefaultRouter()
router.register(r"", ExpenseViewSet, basename="expenses")

urlpatterns = [path("", include(router.urls))]
