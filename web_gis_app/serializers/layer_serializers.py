from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..models import Layer
from .tileset_serializers import TileSetSerializer


class LayerSerializer(BaseModelSerializer):
    bbox = serializers.SerializerMethodField()
    dataset_type = serializers.SerializerMethodField()
    tileset = serializers.SerializerMethodField()

    class Meta:
        model = Layer
        fields = ("id", "name", "source", "style", "bbox", "dataset_type", "tileset")
        read_only_fields = ("id", "bbox", "dataset_type", "tileset")

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

    def get_tileset(self, obj):
        """Get the tileset info if the source dataset has one."""
        if obj.source and hasattr(obj.source, "tileset"):
            try:
                return TileSetSerializer(obj.source.tileset).data
            except obj.source.tileset.RelatedObjectDoesNotExist:
                return None
        return None
