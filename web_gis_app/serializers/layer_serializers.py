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
        Get bounding box from the source dataset's metadata or tileset.
        Returns [minX, minY, maxX, maxY]
        """
        # 1. Try metadata (Vector datasets usually handle this)
        if obj.source and obj.source.metadata and "bbox" in obj.source.metadata:
            return obj.source.metadata.get("bbox")

        # 2. Try tileset (Raster datasets)
        if obj.source and hasattr(obj.source, "tileset"):
            try:
                return obj.source.tileset.bounds
            except obj.source.tileset.RelatedObjectDoesNotExist:
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
