from django.db import models

from shared.constants import AppName

from .base_models import BaseModel


class Notification(BaseModel):
    app_name = models.CharField(max_length=100, choices=AppName)
    content = models.TextField()
    seen = models.BooleanField(default=False)
