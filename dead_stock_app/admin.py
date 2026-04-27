from django.contrib import admin

from .models import Category, InventoryItem, ItemImage, Lead, Report, SearchLog, Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "city", "is_verified", "created_at")
    list_filter = ("is_verified",)
    search_fields = ("name", "city", "pincode", "phone")
    raw_id_fields = ("user",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "shop",
        "category",
        "quantity",
        "price",
        "status",
        "stale_at",
    )
    list_filter = ("status", "condition", "category")
    search_fields = ("name", "sku", "shop__name")
    raw_id_fields = ("shop", "category", "user")


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ("item", "position", "is_primary", "variants_ready", "created_at")
    raw_id_fields = ("item",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("shop", "buyer", "item", "contacted_at", "created_at")
    list_filter = ("contacted_at",)
    raw_id_fields = ("buyer", "shop", "item")
    search_fields = ("shop__name", "buyer__username")


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "result_count", "user", "created_at")
    search_fields = ("query",)
    raw_id_fields = ("user",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "status",
        "reason_excerpt",
        "item",
        "shop",
        "reporter",
        "created_at",
    )
    list_filter = ("status",)
    raw_id_fields = ("item", "shop", "reporter")
    search_fields = ("reason",)

    def reason_excerpt(self, obj):
        return (obj.reason or "")[:60]

    reason_excerpt.short_description = "Reason"
