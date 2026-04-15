"""Serializers for the geoprocessing API."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from ..constants import ProcessingTool
from ..models import Dataset, DatasetNode, ProcessingJob
from ..tool_registry import get_tool

# Tools that require a single-band elevation raster (DEM).
_DEM_ONLY_TOOLS = {
    ProcessingTool.HILLSHADE.value,
    ProcessingTool.SLOPE.value,
    ProcessingTool.CONTOUR.value,
}


class ProcessingJobSerializer(BaseModelSerializer):
    """Read serializer for ProcessingJob."""

    input_dataset_ids = serializers.SerializerMethodField()

    class Meta:
        model = ProcessingJob
        fields = (
            "id",
            "tool_name",
            "status",
            "progress",
            "parameters",
            "input_dataset_ids",
            "output_dataset",
            "output_node",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_input_dataset_ids(self, obj: ProcessingJob) -> list[str]:
        return [str(ds.id) for ds in obj.input_datasets.all()]


class ProcessingJobCreateSerializer(serializers.Serializer):
    """Validate a job submission."""

    tool_name = serializers.CharField()
    input_dataset_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    parameters = serializers.DictField(required=False, default=dict)
    output_name = serializers.CharField(required=False, allow_blank=True)
    output_parent_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_tool_name(self, value: str) -> str:
        try:
            get_tool(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        return value

    def validate(self, attrs):
        user = self.context["request"].user
        tool = get_tool(attrs["tool_name"])

        datasets = list(
            Dataset.objects.filter(
                id__in=attrs["input_dataset_ids"],
                dataset_node__user=user,
            )
        )

        if len(datasets) != len(attrs["input_dataset_ids"]):
            raise serializers.ValidationError(
                {"input_dataset_ids": "One or more datasets not found."}
            )

        for dataset in datasets:
            if dataset.type not in tool.input_types:
                raise serializers.ValidationError(
                    {
                        "input_dataset_ids": (
                            f"Tool '{tool.tool.value}' does not accept datasets of type "
                            f"'{dataset.type}'."
                        )
                    }
                )

            if attrs["tool_name"] in _DEM_ONLY_TOOLS:
                metadata = dataset.metadata or {}
                band_count = metadata.get("band_count")
                raster_kind = metadata.get("raster_kind")

                if raster_kind == "ortho" or (
                    isinstance(band_count, int) and band_count > 1
                ):
                    raise serializers.ValidationError(
                        {
                            "input_dataset_ids": (
                                f"'{tool.label}' requires a single-band elevation raster (DEM). "
                                f"'{dataset.dataset_node.name}' is a {band_count}-band "
                                f"{'orthophoto' if raster_kind == 'ortho' else 'raster'} "
                                f"and cannot be used as input."
                            )
                        }
                    )

        # Validate parameters against the tool's Pydantic model.
        try:
            validated_params = tool.params_model.model_validate(
                attrs.get("parameters", {}) or {}
            ).model_dump()
        except PydanticValidationError as exc:
            raise serializers.ValidationError({"parameters": exc.errors()}) from exc

        # Optional output parent must belong to user.
        parent_id = attrs.get("output_parent_id")

        if parent_id:
            parent_exists = DatasetNode.objects.filter(
                id=parent_id, user=user
            ).exists()

            if not parent_exists:
                raise serializers.ValidationError(
                    {"output_parent_id": "Parent folder not found."}
                )

        attrs["_datasets"] = datasets
        attrs["_validated_params"] = validated_params
        attrs["_tool"] = tool

        return attrs
