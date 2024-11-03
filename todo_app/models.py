from django.db import models

from shared.models import BaseModel


class Task(BaseModel):
    description = models.TextField()
