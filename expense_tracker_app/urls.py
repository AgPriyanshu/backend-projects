from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExpenseViewSet

router = DefaultRouter()
router.register(r"", ExpenseViewSet, basename="expenses")

urlpatterns = [path("", include(router.urls))]
