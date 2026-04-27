import unicodedata
from datetime import timedelta

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import InventoryItem


def normalize_name(text: str) -> str:
    """Lowercase + strip diacritics so trigram search matches across scripts."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


@receiver(pre_save, sender=InventoryItem)
def fill_normalized_and_stale(sender, instance, **kwargs):
    if instance.name:
        instance.name_normalized = normalize_name(instance.name)

    if not instance.stale_at:
        instance.stale_at = timezone.now() + timedelta(days=30)
