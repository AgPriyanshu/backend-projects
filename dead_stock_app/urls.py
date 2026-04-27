from django.urls import path

from .views import OTPRequestView, OTPVerifyView, RefreshTokenView, ping

urlpatterns = [
    path("ping/", ping, name="dead-stock-ping"),
    path("auth/otp/request/", OTPRequestView.as_view(), name="ds-otp-request"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="ds-otp-verify"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="ds-refresh"),
]
