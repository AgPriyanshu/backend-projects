from django.db import models

from shared.models import BaseModel

from .constants import DatasetNodeType, DatasetType, FileFormat


class DatasetNode(BaseModel):
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
        choices=DatasetNodeType.choices(),
        help_text="Node type: folder for organization, dataset for actual data",
    )


class DatasetClosure(BaseModel):
    ancestor = models.ForeignKey(
        DatasetNode,
        on_delete=models.CASCADE,
        help_text="Ancestor node in the hierarchy",
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


class Dataset(BaseModel):
    dataset_node = models.OneToOneField(
        DatasetNode, on_delete=models.CASCADE, related_name="dataset"
    )

    # Basic information
    name = models.CharField(max_length=255, help_text="Display name of the dataset")
    description = models.TextField(
        blank=True, help_text="Detailed description of the dataset content and purpose"
    )

    # Dataset type and format
    type = models.CharField(
        max_length=20,
        choices=DatasetType.choices(),
        help_text="Dataset type: vector, raster, geo_pdf, or document",
    )

    format = models.CharField(
        max_length=20,
        choices=FileFormat.choices(),
        help_text="File format: geojson, shapefile, geotiff, etc.",
    )

    # Cloud storage - base path for the dataset
    cloud_storage_path = models.CharField(
        max_length=500,
        help_text="Cloud storage path. File path for single-file formats, directory path for multi-file formats (e.g., shapefiles)",
    )

    # Geospatial metadata
    srid = models.IntegerField(
        null=True, blank=True, help_text="Spatial Reference System ID (EPSG code)"
    )
    bbox = models.JSONField(
        null=True,
        blank=True,
        help_text="Bounding box [minx, miny, maxx, maxy]",
    )

    # Additional metadata (flexible JSON for format-specific data)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional format-specific metadata (resolution, bands, CRS details, etc.)",
    )

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class DatasetFile(BaseModel):
    """
    Individual files within a dataset.
    For single-file formats (GeoJSON, GeoTIFF): one entry
    For multi-file formats (Shapefile): multiple entries (.shp, .shx, .dbf, .prj, etc.)
    """

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="files",
        help_text="Parent dataset this file belongs to",
    )

    # Cloud storage path for this specific file
    cloud_storage_path = models.CharField(
        max_length=500, help_text="Full cloud storage path to this specific file"
    )

    # File metadata
    file_name = models.CharField(max_length=255, help_text="Original filename")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(
        max_length=100, blank=True, help_text="MIME type of the file"
    )

    # File role (for multi-file formats)
    role = models.CharField(
        max_length=50,
        default="main",
        help_text="File role: 'main' for primary file, or specific roles like 'index', 'attributes', 'projection' for shapefiles",
    )

    class Meta:
        db_table = "dataset_file"
        verbose_name = "Dataset File"
        verbose_name_plural = "Dataset Files"
        unique_together = [["dataset", "role"]]  # One file per role per dataset

    def __str__(self):
        return f"{self.file_name} ({self.role})"
