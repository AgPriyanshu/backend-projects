import json

from django.contrib.gis.geos import GEOSGeometry
from rest_framework_gis.fields import GeometryField
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from shared.serializers import BaseModelSerializer

from ..models.feature_models import Feature


class FeatureSerializer(GeoFeatureModelSerializer, BaseModelSerializer):
    """
    Serializer for the Feature model that outputs valid GeoJSON.
    """

    geometry = GeometryField()

    class Meta:
        model = Feature
        geo_field = "geometry"
        fields = (
            "id",
            "dataset",
            "geometry",
            "properties",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def to_internal_value(self, data):
        # Allow standard GeoFeatureModelSerializer mapping to happen
        parsed_data = super().to_internal_value(data)

        # DRF-GIS might leak raw Geometry dictionaries through ListSerializers on bulk endpoints.
        # Enforce valid GEOSGeometry generation here for proxy database writes natively.
        geom = parsed_data.get("geometry")

        if isinstance(geom, dict):
            try:
                parsed_data["geometry"] = GEOSGeometry(json.dumps(geom))
            except Exception:
                pass

        return parsed_data
