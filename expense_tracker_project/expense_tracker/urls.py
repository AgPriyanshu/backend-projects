"""
URL configuration for expense_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.views.generic import TemplateView
from django.conf.urls.static import static
from django.urls import path
from . import settings
import os


urlpatterns = [
    path(
        "api-doc/",
        TemplateView.as_view(
            template_name=os.path.join(settings.BASE_DIR, "templates/open-api.html"),
        ),
        name="api-doc",
    ),
]

# Adding static file urls.
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Enable api doc url only if debug is true.
if settings.DEBUG:
    urlpatterns.append(
        path(
            "api-doc/",
            TemplateView.as_view(
                template_name="openapi.html",
                extra_context={"schema_url": "openapi-schema"},
            ),
            name="api-doc",
        )
    )
