from django.db import models

from shared.models.base_models import BaseModel


class Expense(BaseModel):
    title = models.TextField()
    spend = models.DecimalField(max_digits=10, decimal_places=2)
