"""TileSet model for storing processed tile-ready file information linked to a Dataset."""

from django.db import models

from shared.models.base_models import BaseModelWithoutUser

from ..constants import TileSetStatus
from .dataset_models import Dataset


class TileSet(BaseModelWithoutUser):
    """Stores metadata about a processed tile-ready file generated from a raster dataset."""

    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        related_name="tileset",
        help_text="Source dataset this tileset was generated from.",
    )

    status = models.CharField(
        max_length=20,
        choices=TileSetStatus.choices,
        default=TileSetStatus.PENDING,
        help_text="Current processing status of the tileset.",
    )

    storage_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Cloud storage path for the processed tile-ready file.",
    )

    file_size = models.BigIntegerField(
        default=0,
        help_text="Size of the processed file in bytes.",
    )

    min_zoom = models.IntegerField(
        default=0,
        help_text="Minimum zoom level for tile serving.",
    )

    max_zoom = models.IntegerField(
        default=22,
        help_text="Maximum zoom level for tile serving.",
    )

    bounds = models.JSONField(
        default=list,
        blank=True,
        help_text="Geographic bounds [west, south, east, north] in EPSG:4326.",
    )

    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if processing failed.",
    )

    class Meta:
        db_table = "tileset"
        verbose_name = "Tile Set"
        verbose_name_plural = "Tile Sets"

    def __str__(self):
        return f"TileSet({self.dataset_id}) - {self.status}"
