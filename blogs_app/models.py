from django.db import models

from shared.models.base_models import BaseModel


class Blog(BaseModel):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=50)
    content = models.TextField()
