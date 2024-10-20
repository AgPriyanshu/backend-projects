from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from blogs_app.views import BlogsViewSet
from .settings import BASE_DIR
import os

# router = DefaultRouter()
# router.register(r"blogs", BlogsViewSet, basename="blog")

# urlpatterns = [path("", include(router.urls))]

urlpatterns = [
    # re_path(
    #     r"^weather/current/(?P<location>[^/]+)",
    #     views.current,
    # ),
    path(
        "api-doc/",
        TemplateView.as_view(
            template_name=os.path.join(BASE_DIR, "templates/open-api.html"),
            extra_context={"schema_url": BASE_DIR / "docs" / "open-api.yaml"},
        ),
        name="api-doc",
    ),
]
