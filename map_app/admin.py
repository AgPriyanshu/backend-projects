from django.contrib import admin
from .models import GeospatialImage, ObjectDetection, DetectedObject


@admin.register(GeospatialImage)
class GeospatialImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'processing_status', 'created_at']
    list_filter = ['processing_status', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ObjectDetection)
class ObjectDetectionAdmin(admin.ModelAdmin):
    list_display = ['geospatial_image', 'model_version', 'confidence_threshold', 'processing_time', 'created_at']
    list_filter = ['model_version', 'created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(DetectedObject)
class DetectedObjectAdmin(admin.ModelAdmin):
    list_display = ['detection', 'object_type', 'confidence_score', 'area']
    list_filter = ['object_type', 'confidence_score']
    search_fields = ['object_type']
    readonly_fields = ['id']
