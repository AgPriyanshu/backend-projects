from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..constants import DatasetNodeType, DatasetType
from ..models import Dataset, DatasetNode
from ..validators import validate_dataset_parent_for_node_type
from .tileset_serializers import TileSetSerializer


class DatasetNodeSerializer(BaseModelSerializer):
    class Meta:
        model = DatasetNode
        fields = ("id", "name", "type", "parent")
        read_only_fields = ("id",)


class DatasetSerializer(BaseModelSerializer):
    tileset = TileSetSerializer(read_only=True)

    class Meta:
        model = Dataset
        fields = (
            "id",
            "dataset_node",
            "type",
            "format",
            "file_name",
            "file_size",
            "cloud_storage_path",
            "metadata",
            "tileset",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )


class DatasetUploadBaseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=DatasetNode.objects.all(), required=False, allow_null=True
    )  # type: ignore
    type = serializers.ChoiceField(choices=DatasetNodeType.choices, required=True)
    dataset_type = serializers.ChoiceField(
        choices=DatasetType.choices, required=False, allow_null=True
    )

    def validate(self, attrs):
        node_type = attrs.get("type")
        parent = attrs.get("parent")

        validate_dataset_parent_for_node_type(
            node_type=node_type,
            parent=parent,
            field_name="parent",
        )

        return attrs


class DatasetUploadSerializer(DatasetUploadBaseSerializer):
    """Serializer for uploading datasets with files"""

    files = serializers.ListField(
        child=serializers.FileField(), required=True, allow_empty=False
    )

    def validate_files(self, value):
        """Validate uploaded files"""
        if not value:
            raise serializers.ValidationError("Exactly one file is required")

        if len(value) != 1:
            raise serializers.ValidationError(
                "Only one file can be uploaded per dataset"
            )

        # Optional: Add file size validation
        max_file_size = 100 * 1024 * 1024  # 100MB
        file = value[0]
        if file.size > max_file_size:
            raise serializers.ValidationError(
                f"File {file.name} exceeds maximum size of 100MB"
            )

        return value


class DatasetNodeTreeSerializer(BaseModelSerializer):
    """Serializer for nested tree structure with children"""

    children = serializers.SerializerMethodField()
    dataset = DatasetSerializer(read_only=True)

    class Meta:
        model = DatasetNode
        fields = ["id", "type", "name", "parent", "children", "dataset", "created_at"]

    def get_children(self, obj):
        """Get direct children of this node"""
        children = (
            DatasetNode.objects.filter(parent=obj)
            .select_related("dataset")
            .order_by("name")
        )
        return DatasetNodeTreeSerializer(children, many=True).data


class DatasetMultipartInitSerializer(DatasetUploadBaseSerializer):
    metadata = serializers.DictField(required=False, default={})


class DatasetMultipartSignSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    key = serializers.CharField()
    part_number = serializers.IntegerField(min_value=1, max_value=10000)


class DatasetMultipartCompleteSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    key = serializers.CharField()
    parts = serializers.ListField(child=serializers.DictField())
