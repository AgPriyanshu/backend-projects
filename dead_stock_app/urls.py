from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    InventoryItemViewSet,
    OTPRequestView,
    OTPVerifyView,
    RefreshTokenView,
    ShopViewSet,
    ping,
)

router = DefaultRouter()
router.register(r"shops", ShopViewSet, basename="ds-shops")
router.register(r"items", InventoryItemViewSet, basename="ds-items")
router.register(r"categories", CategoryViewSet, basename="ds-categories")

urlpatterns = [
    path("ping/", ping, name="dead-stock-ping"),
    path("auth/otp/request/", OTPRequestView.as_view(), name="ds-otp-request"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="ds-otp-verify"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="ds-refresh"),
    path("", include(router.urls)),
]
