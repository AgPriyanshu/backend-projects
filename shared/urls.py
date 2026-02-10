from django.urls import path

from .views.sse import sse_view

urlpatterns = [
    path("events/", sse_view, name="sse-events"),
]
