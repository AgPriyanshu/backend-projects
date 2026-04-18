from __future__ import annotations

from typing import Optional

from django.db import transaction
from pydantic import Field

from shared.schemas import StrictPayload
from shared.workflows.base.base_operation import Operation

from ..constants import (
    DatasetNodeType,
    DatasetStatus,
    DatasetType,
    FileFormat,
    TileSetStatus,
)
from ..helpers import format_to_ext
from ..models import Dataset, DatasetNode, Feature, ProcessingJob, TileSet

# -- Shared output operation --


class CreateOutputDatasetPayload(StrictPayload):
    job_id: str
    output_name: str
    output_parent_id: Optional[str] = None
    output_type: str
    output_format: str = FileFormat.GEOPACKAGE.value
    storage_path: str = ""
    file_size: int = 0
    metadata: dict = Field(default_factory=dict)


class CreateOutputDataset(Operation[CreateOutputDatasetPayload, dict]):
    """Create the DatasetNode + Dataset (+ TileSet if raster) for a processing output."""

    name = "create_output_dataset"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        user = job.user

        metadata = self.payload.metadata or self.ctx.get("raster_output_metadata", {})
        file_size = self.payload.file_size or self.ctx.get("raster_output_file_size", 0)

        parent = None

        if self.payload.output_parent_id:
            parent = DatasetNode.objects.filter(
                pk=self.payload.output_parent_id, user=user
            ).first()

        with transaction.atomic():
            dataset_node = DatasetNode.objects.create(
                name=self.payload.output_name,
                parent=parent,
                type=DatasetNodeType.DATASET.value,
                user=user,
            )

            dataset = Dataset.objects.create(
                dataset_node=dataset_node,
                type=self.payload.output_type,
                format=self.payload.output_format,
                metadata=metadata,
                file_name=f"{self.payload.output_name}.{format_to_ext(self.payload.output_format)}",
                file_size=file_size,
                cloud_storage_path=self.payload.storage_path,
                status=DatasetStatus.PENDING,
            )

            if self.payload.output_type == DatasetType.RASTER.value:
                status = (
                    TileSetStatus.READY
                    if self.payload.output_format == FileFormat.COG.value
                    else TileSetStatus.PENDING
                )
                TileSet.objects.create(
                    dataset=dataset,
                    status=status,
                    storage_path=self.payload.storage_path,
                    file_size=file_size,
                    bounds=metadata.get("bounds", []),
                    min_zoom=metadata.get("min_zoom", 0),
                    max_zoom=metadata.get("max_zoom", 22),
                )

            dataset.status = DatasetStatus.UPLOADED
            dataset.save(update_fields=["status", "updated_at"])

            # Attach the pre-inserted features to this dataset, if any.
            if pending_feature_dataset_id := self.ctx.get("pending_feature_dataset_id"):
                Feature.objects.filter(dataset_id=pending_feature_dataset_id).update(
                    dataset=dataset
                )
                staging_dataset = (
                    Dataset.objects.filter(pk=pending_feature_dataset_id)
                    .select_related("dataset_node")
                    .first()
                )

                if staging_dataset:
                    staging_dataset.dataset_node.delete()

            job.output_dataset = dataset
            job.output_node = dataset_node
            job.save(update_fields=["output_dataset", "output_node", "updated_at"])

        return {
            "dataset_id": str(dataset.id),
            "dataset_node_id": str(dataset_node.id),
        }
