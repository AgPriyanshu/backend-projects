"""Serializers for the TileSet model."""

from shared.serializers import BaseModelSerializer

from ..models import TileSet


class TileSetSerializer(BaseModelSerializer):
    """Read-only serializer for TileSet data."""

    class Meta:
        model = TileSet
        fields = (
            "id",
            "status",
            "storage_path",
            "file_size",
            "min_zoom",
            "max_zoom",
            "bounds",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
