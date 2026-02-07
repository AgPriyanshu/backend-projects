from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..models import Layer


class LayerSerializer(BaseModelSerializer):
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = Layer
        fields = ("id", "name", "source", "style", "bbox")
        read_only_fields = ("id", "bbox")

    def get_bbox(self, obj):
        """Get bounding box from the source dataset's metadata."""
        if obj.source and obj.source.metadata:
            return obj.source.metadata.get("bbox")
        return None
