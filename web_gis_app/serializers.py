from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from .models import Dataset, DatasetFile, DatasetNode


class DatasetNodeSerializer(BaseModelSerializer):
    class Meta:
        model = DatasetNode
        fields = "__all__"


class DatasetSerializer(BaseModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "dataset_node",
            "name",
            "description",
            "type",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "files")


class DatasetUploadSerializer(serializers.Serializer):
    """Serializer for uploading datasets with files"""

    # Node information
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    node_type = serializers.ChoiceField(
        choices=["folder", "dataset"], source="type", required=True
    )

    # Dataset information
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(max_length=20)
    format = serializers.CharField(max_length=20)
    srid = serializers.IntegerField(required=False, allow_null=True)
    bbox = serializers.JSONField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, default=dict)

    # Files
    files = serializers.ListField(
        child=serializers.FileField(), required=True, allow_empty=False
    )

    def validate_parent_id(self, value):
        """Validate that parent node exists"""
        if value is not None:
            if not DatasetNode.objects.filter(id=value).exists():
                raise serializers.ValidationError(f"Parent node with id {value} does not exist")
        return value

    def validate_files(self, value):
        """Validate uploaded files"""
        if not value:
            raise serializers.ValidationError("At least one file is required")

        # Optional: Add file size validation
        max_file_size = 100 * 1024 * 1024  # 100MB
        for file in value:
            if file.size > max_file_size:
                raise serializers.ValidationError(
                    f"File {file.name} exceeds maximum size of 100MB"
                )

        return value


class DatasetFileSerializer(BaseModelSerializer):
    class Meta:
        model = DatasetFile
        fields = "__all__"


class DatasetNodeTreeSerializer(BaseModelSerializer):
    """Serializer for nested tree structure with children"""

    children = serializers.SerializerMethodField()
    dataset = DatasetSerializer(read_only=True)

    class Meta:
        model = DatasetNode
        fields = ["id", "type", "parent", "children", "dataset", "created_at", "updated_at"]

    def get_children(self, obj):
        """Get direct children of this node"""
        children = DatasetNode.objects.filter(parent=obj).select_related("dataset")
        return DatasetNodeTreeSerializer(children, many=True).data
