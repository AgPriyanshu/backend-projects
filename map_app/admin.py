from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Layer, Feature, FeatureAttribute


class FeatureAttributeInline(admin.TabularInline):
    model = FeatureAttribute
    extra = 0
    fields = ["key", "value", "data_type", "numeric_value", "date_value"]
    readonly_fields = ["data_type", "numeric_value", "date_value"]


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at", "feature_count"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["name", "description"]

    def feature_count(self, obj):
        return obj.features.count()

    feature_count.short_description = "Features"


@admin.register(Feature)
class FeatureAdmin(GISModelAdmin):
    list_display = ["__str__", "layer", "created_at", "attribute_count"]
    list_filter = ["layer", "created_at"]
    search_fields = ["layer__name"]
    inlines = [FeatureAttributeInline]

    def attribute_count(self, obj):
        return obj.attributes.count()

    attribute_count.short_description = "Attributes"


@admin.register(FeatureAttribute)
class FeatureAttributeAdmin(admin.ModelAdmin):
    list_display = ["feature", "key", "value", "data_type", "created_at"]
    list_filter = ["key", "data_type", "created_at"]
    search_fields = ["key", "value", "feature__layer__name"]
    readonly_fields = ["data_type", "numeric_value", "date_value"]
    raw_id_fields = ["feature"]
