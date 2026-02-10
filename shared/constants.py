from enum import StrEnum

from django.db.models import TextChoices


class BaseEnum(StrEnum):
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]


class AppName(TextChoices):
    WEB_GIS_APP = "web_gis_app"
    EXPENSE_TRACKER_APP = "expense_tracker_app"
    BACKEND_PROJECTS = "backend_projects"
