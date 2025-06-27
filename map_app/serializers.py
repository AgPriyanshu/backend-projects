from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry
import json
from .models import Layer, Feature, FeatureAttribute


class FeatureAttributeSerializer(serializers.ModelSerializer):
    typed_value = serializers.ReadOnlyField(source="get_typed_value")

    class Meta:
        model = FeatureAttribute
        fields = ["key", "value", "data_type", "typed_value"]


class FeatureSerializer(serializers.ModelSerializer):
    attributes = FeatureAttributeSerializer(many=True, read_only=True)
    geometry_wkt = serializers.CharField(source="geometry.wkt", read_only=True)

    class Meta:
        model = Feature
        fields = ["id", "geometry_wkt", "attributes", "created_at", "updated_at"]


class LayerSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)
    feature_count = serializers.IntegerField(source="features.count", read_only=True)

    class Meta:
        model = Layer
        fields = [
            "id",
            "name",
            "description",
            "feature_count",
            "features",
            "created_at",
            "updated_at",
        ]


class LayerListSerializer(serializers.ModelSerializer):
    feature_count = serializers.IntegerField(source="features.count", read_only=True)

    class Meta:
        model = Layer
        fields = [
            "id",
            "name",
            "description",
            "feature_count",
            "created_at",
            "updated_at",
        ]


class LayerGeoJSONSerializer(serializers.ModelSerializer):
    """Serializer for Layer as GeoJSON format for map visualization"""
    geojson = serializers.SerializerMethodField()
    
    class Meta:
        model = Layer
        fields = ["id", "name", "description", "geojson", "created_at", "updated_at"]
    
    def get_geojson(self, obj):
        """Convert layer features to GeoJSON format"""
        features = []
        for feature in obj.features.all():
            try:
                # Convert geometry to GeoJSON - use json.loads instead of eval
                geometry = json.loads(feature.geometry.geojson)
                
                # Collect attributes as properties
                properties = {}
                for attr in feature.attributes.all():
                    properties[attr.key] = attr.get_typed_value()
                
                features.append({
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties
                })
            except Exception as e:
                # Log the error but continue processing other features
                print(f"Error processing feature {feature.id}: {e}")
                continue
        
        return {
            "type": "FeatureCollection",
            "features": features
        }


class ShapefileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    layer_name = serializers.CharField(max_length=255)
    description = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )

    def validate_file(self, value):
        if not value.name.endswith(".zip"):
            raise serializers.ValidationError(
                "File must be a ZIP archive containing shapefile components."
            )
        return value
