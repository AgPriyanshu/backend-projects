from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Cart


@receiver(m2m_changed, sender=Cart.products.through)
def update_cart_count(sender, instance, action, *args, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        instance.count = instance.products.count()
        instance.save(update_fields=["count"])
        instance.save(update_fields=["count"])
