from django.core import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import Cart, Product


@receiver(m2m_changed, sender=Cart.products.through)
def update_cart_count(sender, instance, action, *args, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        instance.count = instance.products.count()
        instance.save(update_fields=["count"])
        instance.save(update_fields=["count"])


@receiver([post_save, post_delete], sender=Product)
def clear_product_cache(sender, **kwargs):
    cache.delete("products_list")
