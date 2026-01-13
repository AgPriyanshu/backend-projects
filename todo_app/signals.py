from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import increment_user_cache_version
from .models import Task


@receiver([post_save, post_delete], sender=Task)
def increment_task_cache_version(sender, instance, **kwargs):
    """Increment cache version when a task is created, updated, or deleted."""
    increment_user_cache_version(instance.user_id)
