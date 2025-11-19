from django.contrib import admin

from .models import Cart, Category, Product

# class EcommerceAdminSite(admin.AdminSite):
#     site_header = "E-Com Management"


@admin.register(Cart)
class CartModelAdmin(admin.ModelAdmin):
    list_display = ("count",)


@admin.register(Category)
class CategoryModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )


@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
