import uuid

from django.contrib.auth.models import User
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_id=models.ForeignKey(User, on_delete=models.DO_NOTHING)

    class Meta:
        abstract = True

    def __str__(self):
        return super().__str__()
