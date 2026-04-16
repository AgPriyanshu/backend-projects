from django.db import connection
from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..models import Layer
from .tileset_serializers import TileSetSerializer


class LayerSerializer(BaseModelSerializer):
    bbox = serializers.SerializerMethodField()
    dataset_type = serializers.SerializerMethodField()
    raster_kind = serializers.SerializerMethodField()
    band_count = serializers.SerializerMethodField()
    tileset = serializers.SerializerMethodField()

    class Meta:
        model = Layer
        fields = (
            "id",
            "name",
            "source",
            "style",
            "bbox",
            "dataset_type",
            "raster_kind",
            "band_count",
            "tileset",
        )
        read_only_fields = ("id", "bbox", "dataset_type", "raster_kind", "band_count", "tileset")

    def get_bbox(self, obj):
        """
        Get bounding box from the source dataset.
        Returns [minLng, minLat, maxLng, maxLat] (EPSG:4326).
        """
        if not obj.source:
            return None

        # Raster: try metadata bounds then tileset bounds.
        if obj.source.type == "raster":
            bounds = (obj.source.metadata or {}).get("bounds")

            if bounds:
                return bounds

            if hasattr(obj.source, "tileset"):
                try:
                    return obj.source.tileset.bounds
                except obj.source.tileset.RelatedObjectDoesNotExist:
                    pass

            return None

        # Vector: compute from PostGIS ST_Extent so it works even without stored metadata.
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        ST_XMin(extent), ST_YMin(extent),
                        ST_XMax(extent), ST_YMax(extent)
                    FROM (
                        SELECT ST_Extent(ST_Transform(geometry, 4326)) AS extent
                        FROM feature
                        WHERE dataset_id = %s
                    ) sub
                    """,
                    [str(obj.source_id)],
                )
                row = cursor.fetchone()

            if row and row[0] is not None:
                return [row[0], row[1], row[2], row[3]]
        except Exception:
            pass

        return None

    def get_dataset_type(self, obj):
        """Get the type of the source dataset (vector, raster, text)."""
        if obj.source:
            return obj.source.type
        return None

    def get_raster_kind(self, obj):
        if not obj.source:
            return None
        return (obj.source.metadata or {}).get("raster_kind")

    def get_band_count(self, obj):
        if not obj.source:
            return None
        return (obj.source.metadata or {}).get("band_count")

    def get_tileset(self, obj):
        """Get the tileset info if the source dataset has one."""
        if obj.source and hasattr(obj.source, "tileset"):
            try:
                return TileSetSerializer(obj.source.tileset).data
            except obj.source.tileset.RelatedObjectDoesNotExist:
                return None
        return None
