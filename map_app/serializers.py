from rest_framework import serializers
from .models import GeospatialImage, ObjectDetection, DetectedObject


class GeospatialImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeospatialImage
        fields = '__all__'
        read_only_fields = ('user', 'processed_image', 'processing_status', 'created_at', 'updated_at')


class DetectedObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectedObject
        fields = '__all__'


class ObjectDetectionSerializer(serializers.ModelSerializer):
    objects = DetectedObjectSerializer(many=True, read_only=True)
    
    class Meta:
        model = ObjectDetection
        fields = '__all__'


class GeospatialImageDetailSerializer(serializers.ModelSerializer):
    detections = ObjectDetectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = GeospatialImage
        fields = '__all__'


