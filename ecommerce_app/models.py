import uuid

from django.contrib.auth.models import User
from django.db import models
from djmoney.models.fields import MoneyField

from shared.models import BaseModelWithoutUser


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING)
    price = MoneyField(
        max_digits=9,
        decimal_places=2,
    )
    stock = models.IntegerField(default=0)
    added_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(BaseModelWithoutUser):
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    quantity = models.IntegerField(default=0)


class Cart(BaseModelWithoutUser):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    items = models.ManyToManyField(
        CartItem,
        related_name="cart",
    )
    count = models.IntegerField(default=0, editable=False)
