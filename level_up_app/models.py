from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shared.models.base_models import BaseModel


class Character(BaseModel):
    name = models.CharField(max_length=40)
    avatar = models.TextField()
    class_name = models.CharField(max_length=40)
    level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(999)],
    )

    class Meta:
        ordering = ["created_at"]


class Stat(BaseModel):
    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="stats"
    )
    name = models.CharField(max_length=50)
    value = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    max = models.IntegerField(default=5, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["created_at"]
