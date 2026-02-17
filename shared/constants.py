from enum import StrEnum

from django.db.models import TextChoices


class BaseEnum(StrEnum):
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]


class AppName(TextChoices):
    WEB_GIS = "web_gis_app"
    MAIN = "backend_projects"
