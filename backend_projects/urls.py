import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from .settings import BASE_DIR, STATIC_ROOT, STATIC_URL
from .views import ping

urlpatterns = [
    path(r"admin/", admin.site.urls),
    path(r"auth/", include("auth_app.urls")),
    path(r"blogs/", include("blogs_app.urls")),
    path(r"weather/", include("weather_app.urls")),
    path(r"tasks/", include("todo_app.urls")),
    path(r"expenses/", include("expense_tracker_app.urls")),
    path(r"notes/", include("note_markdown_app.urls")),
    path(r"urls/", include("url_shortner_app.urls")),
    path(
        "expense-app/api-doc/",
        TemplateView.as_view(
            template_name=os.path.join(
                BASE_DIR, "templates/expense-tracker-open-api.html"
            ),
        ),
        name="expense-api-doc",
    ),
    path(
        "note-app/api-doc/",
        TemplateView.as_view(
            template_name=os.path.join(
                BASE_DIR, "templates/note-markdown-open-api.html"
            ),
        ),
        name="note-api-doc",
    ),
    path("ping/", ping),
    # TODO: Add API Doc for each app
] + static(STATIC_URL, document_root=STATIC_ROOT)


if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
