from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from blogs_app.views import BlogsViewSet
from .settings import BASE_DIR
import os

urlpatterns = [
    path(r"auth/", include("auth_app.urls")),
    path(r"blogs/", include("blogs_app.urls")),
    path(r"weather/", include("weather_app.urls")),
    path(r"tasks/", include("todo_app.urls")),
    # TODO: Add API Doc for each app
    # path(
    #     "api-doc/",
    #     TemplateView.as_view(
    #         template_name=os.path.join(BASE_DIR, "templates/open-api.html"),
    #         extra_context={"schema_url": BASE_DIR / "docs" / "open-api.yaml"},
    #     ),
    #     name="api-doc",
    # ),
]
