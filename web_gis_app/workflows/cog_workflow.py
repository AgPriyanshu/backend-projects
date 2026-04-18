import os

from rasterio.warp import transform_bounds
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from shared.schemas import StrictPayload
from shared.workflows.base.base_operation import Operation
from shared.workflows.base.base_workflow import Workflow
from shared.workflows.operations.download import Download
from shared.workflows.operations.upload import Upload

from ..constants import TileSetStatus
from ..helpers import get_raster_info, get_raster_kind
from ..models import TileSet
from ..notifications import send_notification


class GenerateCOGPayload(StrictPayload):
    input_path: str
    work_dir: str


class UpdateTileSetPayload(StrictPayload):
    tileset_id: str
    storage_path: str


class GenerateCOG(Operation[GenerateCOGPayload, dict]):
    name = "generate_cog"

    def execute(self, *args, **kwargs):
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

        raster_info = get_raster_info(output_path)

        if raster_info.crs and raster_info.crs.to_string() != "EPSG:4326":
            bounds_4326 = transform_bounds(
                raster_info.crs, "EPSG:4326", *raster_info.bounds
            )
            bounds = list(bounds_4326)
        else:
            bounds = list(raster_info.bounds)

        file_size = os.path.getsize(output_path)
        band_count = raster_info.band_count
        raster_kind = get_raster_kind(band_count)

        self.ctx["tileset_metadata"] = {
            "file_size": file_size,
            "bounds": bounds,
            "min_zoom": raster_info.minzoom,
            "max_zoom": raster_info.maxzoom,
            "band_count": band_count,
            "raster_kind": raster_kind,
        }


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

        dataset = tileset.dataset
        dataset_metadata = dict(dataset.metadata or {})
        dataset_metadata["band_count"] = tileset_metadata.get("band_count", 0)
        dataset_metadata["raster_kind"] = tileset_metadata.get("raster_kind", "raster")
        dataset.metadata = dataset_metadata
        dataset.save(update_fields=["metadata"])

        user = dataset.dataset_node.user
        dataset_name = dataset.dataset_node.name

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
