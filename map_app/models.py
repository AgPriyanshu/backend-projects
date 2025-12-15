from django.db import models
from django.contrib.auth.models import User
import uuid


class GeospatialImage(models.Model):
    """Model to store uploaded geospatial images and their metadata"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='geospatial_images')
    name = models.CharField(max_length=255)
    original_image = models.ImageField(upload_to='geospatial_images/originals/')
    processed_image = models.ImageField(upload_to='geospatial_images/processed/', blank=True, null=True)
    bounds = models.JSONField(help_text="Geographic bounds as [west, south, east, north]", blank=True, null=True)
    center_lat = models.FloatField(blank=True, null=True)
    center_lng = models.FloatField(blank=True, null=True)
    zoom_level = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class ObjectDetection(models.Model):
    """Model to store SAM-Geo object detection results"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    geospatial_image = models.ForeignKey(GeospatialImage, on_delete=models.CASCADE, related_name='detections')
    detection_data = models.JSONField(help_text="GeoJSON format detection results")
    confidence_threshold = models.FloatField(default=0.5)
    model_version = models.CharField(max_length=50, default='vit_h')
    processing_time = models.FloatField(help_text="Processing time in seconds", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Detection for {self.geospatial_image.name}"


class DetectedObject(models.Model):
    """Model to store individual detected objects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    detection = models.ForeignKey(ObjectDetection, on_delete=models.CASCADE, related_name='objects')
    geometry = models.JSONField(help_text="GeoJSON geometry of the detected object")
    properties = models.JSONField(help_text="Object properties like confidence, area, etc.")
    object_type = models.CharField(max_length=100, blank=True, null=True)
    confidence_score = models.FloatField()
    area = models.FloatField(help_text="Area in square meters", blank=True, null=True)
    
    class Meta:
        ordering = ['-confidence_score']

    def __str__(self):
        return f"Object {self.object_type or 'Unknown'} - {self.confidence_score:.2f}"


