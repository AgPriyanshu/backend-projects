import uuid

from django.db import models

from shared.models import BaseModel


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.TextField()


class Product(BaseModel):
    name = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=3)
    quantity = models.IntegerField(default=0)


class Cart(BaseModel):
    products = models.ManyToManyField(Product)
    count = models.IntegerField(default=0, editable=False)
