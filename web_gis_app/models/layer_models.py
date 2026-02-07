from django.db import models

from shared.models import BaseModel

from .dataset_models import Dataset


class Layer(BaseModel):
    name = models.TextField()
    source = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    style = models.JSONField(
        default=dict,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.style:
            self.style = self._get_default_style()
        self.full_clean()
        return super().save(*args, **kwargs)

    def _get_default_style(self) -> dict:
        """Return default MapLibre style spec based on source type."""
        from ..constants import DatasetType

        source_type = self.source.type

        if source_type == DatasetType.VECTOR:
            # Vector layers can contain multiple geometry types.
            # Provide default styles for all: points, lines, and polygons.
            return {
                "point": {
                    "type": "circle",
                    "paint": {
                        "circle-radius": 5,
                        "circle-color": "#007cbf",
                        "circle-stroke-width": 1,
                        "circle-stroke-color": "#ffffff",
                    },
                },
                "line": {
                    "type": "line",
                    "paint": {
                        "line-color": "#007cbf",
                        "line-width": 2,
                    },
                },
                "polygon": {
                    "type": "fill",
                    "paint": {
                        "fill-color": "#007cbf",
                        "fill-opacity": 0.4,
                        "fill-outline-color": "#005a8c",
                    },
                },
            }
        elif source_type == DatasetType.RASTER:
            return {
                "type": "raster",
                "paint": {
                    "raster-opacity": 1,
                },
            }

        return {}
