from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..constants import DatasetNodeType, DatasetType
from ..models import Dataset, DatasetNode
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


class DatasetUploadSerializer(serializers.Serializer):
    """Serializer for uploading datasets with files"""

    name = serializers.CharField(max_length=255)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=DatasetNode.objects.all(), required=False, allow_null=True
    )  # type: ignore
    type = serializers.ChoiceField(choices=DatasetNodeType.choices, required=True)
    dataset_type = serializers.ChoiceField(
        choices=DatasetType.choices, required=False, allow_null=True
    )

    files = serializers.ListField(
        child=serializers.FileField(), required=True, allow_empty=False
    )

    def validate(self, attrs):
        """Cross-field validation: dataset nodes cannot have dataset parents"""
        node_type = attrs.get("type")
        parent_id = attrs.get("parent_id")

        # If creating a dataset node with a parent, ensure parent is a folder
        if node_type == DatasetNodeType.DATASET.value and parent_id is not None:
            parent_node = DatasetNode.objects.get(id=parent_id)
            if parent_node.type == DatasetNodeType.DATASET.value:
                raise serializers.ValidationError(
                    {
                        "parent_id": "A dataset node cannot have another dataset as its parent. Parent must be a folder."
                    }
                )

        return attrs

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


class DatasetMultipartInitSerializer(serializers.Serializer):
    """Serializer for initiating a multipart upload"""

    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=DatasetNodeType.choices, required=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=DatasetNode.objects.all(), required=False, allow_null=True
    )
    dataset_type = serializers.ChoiceField(
        choices=DatasetType.choices, required=False, allow_null=True
    )
    metadata = serializers.DictField(required=False, default={})

    def validate(self, attrs):
        """Cross-field validation"""
        node_type = attrs.get("type")
        parent = attrs.get("parent")

        if node_type == DatasetNodeType.DATASET.value and parent is not None:
            if parent.type == DatasetNodeType.DATASET.value:
                raise serializers.ValidationError(
                    "A dataset node cannot have another dataset as its parent. Parent must be a folder."
                )
        return attrs


class DatasetMultipartSignSerializer(serializers.Serializer):
    """Serializer for getting a presigned URL for a part"""

    upload_id = serializers.CharField()
    key = serializers.CharField()
    part_number = serializers.IntegerField(min_value=1, max_value=10000)


class DatasetMultipartCompleteSerializer(serializers.Serializer):
    """Serializer for completing a multipart upload"""

    upload_id = serializers.CharField()
    key = serializers.CharField()
    parts = serializers.ListField(
        child=serializers.DictField()
    )  # List of {ETag: str, PartNumber: int}
