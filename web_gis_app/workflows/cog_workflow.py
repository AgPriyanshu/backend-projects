import math
import os

import rasterio
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from shared.workflows.base.base_operation import Operation
from shared.workflows.base.base_workflow import Workflow
from shared.workflows.operations.download import Download
from shared.workflows.operations.upload import Upload
from shared.workflows.schemas import StrictPayload

from ..constants import TileSetStatus
from ..models import TileSet
from ..notifications import send_notification


class GenerateCOGPayload(StrictPayload):
    """Payload for converting a raster to a Cloud Optimized GeoTIFF."""

    input_path: str
    work_dir: str


class UpdateTileSetPayload(StrictPayload):
    """Payload for updating the TileSet record with processed file metadata."""

    tileset_id: str
    storage_path: str


class GenerateCOG(Operation[GenerateCOGPayload, dict]):
    """Convert a raster file to Cloud Optimized GeoTIFF."""

    name = "generate_cog"

    def execute(self, *args, **kwargs) -> dict:
        input_path = self.payload.input_path
        work_dir = self.payload.work_dir
        output_path = os.path.join(work_dir, "output.tif")

        # Use LZW compression profile for COG.
        output_profile = cog_profiles.get("lzw")

        cog_translate(
            input_path,
            output_path,
            output_profile,
            overview_level=6,
            quiet=True,
        )

        # Extract metadata from the generated COG.
        with rasterio.open(output_path) as src:
            bounds = list(src.bounds)
            file_size = os.path.getsize(output_path)

            # Estimate zoom levels from resolution.
            res = src.res[0]
            max_zoom = self._resolution_to_zoom(res)
            min_zoom = max(0, max_zoom - 10)

        # Write metadata to shared context for downstream operations.
        self.ctx["tileset_metadata"] = {
            "file_size": file_size,
            "bounds": bounds,
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
        }


    @staticmethod
    def _resolution_to_zoom(resolution_degrees: float) -> int:
        """Estimate max zoom level from pixel resolution in degrees."""
        if resolution_degrees <= 0:
            return 18
        zoom = math.log2(360.0 / (resolution_degrees * 256))
        return min(22, max(0, int(zoom)))


class UpdateTileSet(Operation[UpdateTileSetPayload, dict]):
    """Update the TileSet model with the processed file metadata."""

    name = "update_tileset"

    def execute(self, *args, **kwargs) -> dict:
        tileset_metadata = self.ctx.get("tileset_metadata", {})

        tileset = TileSet.objects.get(id=self.payload.tileset_id)
        tileset.status = TileSetStatus.READY
        tileset.storage_path = self.payload.storage_path
        tileset.file_size = tileset_metadata.get("file_size", 0)
        tileset.bounds = tileset_metadata.get("bounds", [])
        tileset.min_zoom = tileset_metadata.get("min_zoom", 0)
        tileset.max_zoom = tileset_metadata.get("max_zoom", 22)
        tileset.save()

        # Send notification to the user.
        user = tileset.dataset.dataset_node.user
        dataset_name = tileset.dataset.dataset_node.name
        send_notification(
            f"Tileset generation completed for dataset '{dataset_name}'.",
            user=user,
        )

        return {
            "tileset_id": str(tileset.id),
            "status": tileset.status,
        }


class COGWorkflow(Workflow):
    """
    Workflow to process an orthomosaic raster into a tile-ready COG.

    Operations run sequentially:
    1. Download — fetch source from object storage (shared operation).
    2. GenerateCOG — convert to Cloud Optimized GeoTIFF.
    3. Upload — push result back to object storage (shared operation).
    4. UpdateTileSet — update the TileSet record.
    """

    name = "cog_workflow"
    operations = (Download, GenerateCOG, Upload, UpdateTileSet)
