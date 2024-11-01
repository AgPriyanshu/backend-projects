from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf.urls.static import static
from .settings import BASE_DIR, STATIC_ROOT, STATIC_URL
import os
from .env_variables import EnvVariable

urlpatterns = [
    path(r"auth/", include("auth_app.urls")),
    path(r"blogs/", include("blogs_app.urls")),
    path(r"weather/", include("weather_app.urls")),
    path(r"tasks/", include("todo_app.urls")),
    path(
        "expense-app/api-doc/",
        TemplateView.as_view(
            template_name=os.path.join(
                BASE_DIR, "templates/expense-tracker-open-api.html"
            ),
        ),
        name="api-doc",
    ),
    # TODO: Add API Doc for each app
] + static(STATIC_URL, document_root=STATIC_ROOT)

if EnvVariable.DEBUG.value == 1:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns + debug_toolbar_urls()
