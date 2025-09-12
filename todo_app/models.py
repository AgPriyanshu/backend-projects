from django.db import models
from django.utils import timezone

from shared.models import BaseModel


class Task(BaseModel):
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def mark_done(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

    def mark_undone(self):
        self.is_completed = False
        self.completed_at = None
        self.save()
