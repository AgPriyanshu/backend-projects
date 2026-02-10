from django.contrib.gis.db import models as gis_models
from django.db import models

from shared.models.base_models import BaseModelWithoutUser

from .dataset_models import Dataset


class Feature(BaseModelWithoutUser):
    """
    Stores individual GeoJSON features with PostGIS geometry.
    Each feature belongs to a dataset and contains geometry + properties.
    """

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="features",
        help_text="The dataset this feature belongs to.",
    )

    geometry = gis_models.GeometryField(
        srid=4326,
        help_text="PostGIS geometry (Point, LineString, Polygon, etc.).",
    )

    properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature properties from the GeoJSON.",
    )

    class Meta:
        db_table = "feature"
        verbose_name = "Feature"
        verbose_name_plural = "Features"
        indexes = [
            models.Index(fields=["dataset"]),
        ]
