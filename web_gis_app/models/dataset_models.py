from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from shared.models.base_models import BaseModel, BaseModelWithoutUser

from ..constants import DatasetNodeType, DatasetStatus, DatasetType, FileFormat


class DatasetNodeQuerySet(models.QuerySet["DatasetNode"]):
    def descendants_of(self, node: DatasetNode) -> DatasetNodeQuerySet:
        return self.filter(descendant_closures__ancestor=node)

    def with_dataset(self) -> DatasetNodeQuerySet:
        return self.select_related("dataset")

    def descendants_with_dataset(self, node: DatasetNode) -> DatasetNodeQuerySet:
        return self.descendants_of(node).with_dataset()


class DatasetNodeManager(models.Manager.from_queryset(DatasetNodeQuerySet)):
    def get_queryset(self) -> DatasetNodeQuerySet:
        return DatasetNodeQuerySet(self.model, using=self._db)

    def descendants_of(self, node: DatasetNode) -> DatasetNodeQuerySet:
        return self.get_queryset().descendants_of(node)

    def with_dataset(self) -> DatasetNodeQuerySet:
        return self.get_queryset().with_dataset()

    def descendants_with_dataset(self, node: DatasetNode) -> DatasetNodeQuerySet:
        return self.get_queryset().descendants_with_dataset(node)


class DatasetNode(BaseModel):
    objects: DatasetNodeManager = DatasetNodeManager()

    name = models.TextField(help_text="Name of the node", default="New Folder")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent node in the hierarchy. Null for root nodes.",
    )
    type = models.CharField(
        max_length=20,
        choices=DatasetNodeType.choices,
        help_text="Node type: folder for organization, dataset for actual data",
    )

    if TYPE_CHECKING:
        dataset: "Dataset"


class DatasetClosure(BaseModelWithoutUser):
    ancestor = models.ForeignKey(
        DatasetNode,
        on_delete=models.CASCADE,
        help_text="Ancestor node in the hierarchy",
        related_name="ancestor_closures",
    )
    descendant = models.ForeignKey(
        DatasetNode,
        on_delete=models.CASCADE,
        related_name="descendant_closures",
        help_text="Descendant node in the hierarchy",
    )
    depth = models.IntegerField(
        help_text="Distance between ancestor and descendant (0 for self-reference)"
    )

    class Meta:
        unique_together = [("ancestor", "descendant")]


class Dataset(BaseModelWithoutUser):
    dataset_node = models.OneToOneField(
        DatasetNode, on_delete=models.CASCADE, related_name="dataset"
    )

    type = models.CharField(
        max_length=20,
        choices=DatasetType.choices,
        help_text="Dataset type: vector, raster, geo_pdf, or document",
    )

    format = models.CharField(
        max_length=20,
        choices=FileFormat.choices,
        help_text="File format: geojson, shapefile, geotiff, etc.",
    )

    file_name = models.CharField(max_length=255, help_text="Primary file name")
    file_size = models.BigIntegerField(help_text="Primary file size in bytes")
    cloud_storage_path = models.CharField(
        max_length=500, help_text="Cloud storage path for the primary file"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional format-specific metadata (resolution, bands, CRS details, etc.)",
    )

    status = models.CharField(
        max_length=20,
        choices=DatasetStatus.choices,
        default=DatasetStatus.UPLOADED,
        help_text="Upload status of the dataset file",
    )

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
