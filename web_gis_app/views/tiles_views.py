"""Views for serving map tiles from processed raster datasets."""

import logging
import os
from typing import Optional

import rasterio
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import Reader

from shared.infrastructure import InfraManager

from ..constants import TileSetStatus
from ..models import TileSet

logger = logging.getLogger(__name__)


class DatasetTileView(APIView):
    """
    Serve XYZ map tiles from a processed raster dataset.

    GET /datasets/<dataset_id>/tiles/<z>/<x>/<y>.png
    """

    permission_classes = [AllowAny]

    def get(self, request, pk, z, x, y):
        """Return a PNG tile for the given ZXY coordinates."""
        try:
            tileset = TileSet.objects.select_related("dataset").get(dataset_id=pk)
        except TileSet.DoesNotExist:
            return Response(
                {"error": "No tileset found for this dataset."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if tileset.status != TileSetStatus.READY:
            return Response(
                {
                    "error": f"Tileset is not ready. Current status: {tileset.status}.",
                    "status": tileset.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not tileset.storage_path:
            return Response(
                {"error": "Tileset has no associated file."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Build the full object storage URL for rio-tiler to read.
            storage_url = self._build_storage_url(tileset.storage_path)

            # Configure rasterio/GDAL environment for S3 access
            rio_env = self._get_rio_env()
            session = self._get_aws_session()

            with rasterio.Env(session=session, **rio_env):
                with Reader(storage_url) as src:
                    # Optional API override:
                    # terrain=true (or raster_dem=true / visualization=terrain)
                    # forces Terrain-RGB encoding for this tile request.
                    force_terrain = self._get_terrain_override(request)

                    is_elevation = force_terrain
                    if is_elevation is None:
                        is_elevation = self._is_elevation_raster(tileset)
                    if is_elevation is None:
                        preview_tile = src.tile(x, y, z, resampling_method="bilinear")
                        is_elevation = (
                            preview_tile.data.ndim == 3 and preview_tile.data.shape[0] == 1
                        )

                    # Elevation rasters (single-band) are encoded as Terrain-RGB.
                    if is_elevation:
                        import numpy as np
                        from rio_rgbify.encoders import data_to_rgb
                        from rio_tiler.models import ImageData

                        # Fetch raw float data, bilinear is better for continuous elevation
                        tile_data = src.tile(x, y, z, resampling_method="bilinear")
                        data = tile_data.data.astype(np.float32)

                        # Handle no-data / NaNs
                        data = np.nan_to_num(data, nan=-10000.0)

                        # rio_rgbify expects a 2D array for a single band DEM.
                        if data.ndim == 3 and data.shape[0] == 1:
                            data_2d = data[0]
                        else:
                            data_2d = data

                        # Encode using Mapbox baseval=-10000, interval=0.1
                        rgb_array = data_to_rgb(data_2d, baseval=-10000.0, interval=0.1)

                        # Create new ImageData to render
                        rgb_tile = ImageData(
                            rgb_array,
                            tile_data.mask,
                            assets=tile_data.assets,
                            bounds=tile_data.bounds,
                            crs=tile_data.crs
                        )
                        content = rgb_tile.render(img_format="PNG")
                    else:
                        tile_data = src.tile(x, y, z)
                        content = tile_data.render(img_format="PNG")

            return HttpResponse(content, content_type="image/png")

        except TileOutsideBounds:
            return Response(
                {"error": "Tile outside of dataset bounds"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Error serving tile z={z}/x={x}/y={y}: {e}")
            return Response(
                {"error": f"Failed to generate tile: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _build_storage_url(storage_path: str) -> str:
        """
        Build the full S3/MinIO URL for rio-tiler to access the file.
        """
        storage = InfraManager.object_storage
        # Fix: K8sObjectStorage uses 'default_bucket', not 'bucket_name'
        bucket = getattr(storage, "default_bucket", "default")
        # Use S3-style path for rio-tiler.
        return f"s3://{bucket}/{storage_path}"

    @staticmethod
    def _get_aws_session():
        """
        Create a rasterio AWSSession with the correct credentials and endpoint.
        """
        from rasterio.session import AWSSession

        use_unsigned = os.environ.get("S3_USE_UNSIGNED", "false").lower() == "true"
        endpoint = os.environ.get("S3_ENDPOINT", "")
        region = os.environ.get("S3_REGION", "us-east-1")

        if use_unsigned:
            return AWSSession(
                aws_unsigned=True,
                region_name=region,
                endpoint_url=endpoint,
            )
        else:
            return AWSSession(
                aws_access_key_id=os.environ.get("S3_ACCESS_KEY", ""),
                aws_secret_access_key=os.environ.get("S3_SECRET_KEY", ""),
                region_name=region,
                endpoint_url=endpoint,
            )

    @staticmethod
    def _get_rio_env() -> dict:
        """
        Get additional GDAL environment configuration.
        """
        return {
            "AWS_S3_ENDPOINT": os.environ.get("S3_ENDPOINT", ""),
            "AWS_REGION": os.environ.get("S3_REGION", "us-east-1"),
            "AWS_HTTPS": "NO",  # Assuming internal SeaweedFS is HTTP; change if HTTPS
            "AWS_VIRTUAL_HOSTING": "FALSE", # Path-style access for MinIO/SeaweedFS
            # Ensure GDAL knows we are treating this as S3
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
        }

    @staticmethod
    def _is_elevation_raster(tileset: TileSet) -> Optional[bool]:
        dataset_metadata = tileset.dataset.metadata or {}
        raster_kind = dataset_metadata.get("raster_kind")
        band_count = dataset_metadata.get("band_count")

        if raster_kind in {"elevation", "ortho"}:
            return raster_kind == "elevation"

        if isinstance(band_count, int):
            return band_count == 1

        return None

    @staticmethod
    def _get_terrain_override(request) -> Optional[bool]:
        """
        Parse optional terrain override query params.

        Supported:
        - ?terrain=true|false
        - ?raster_dem=true|false
        - ?visualization=terrain|terrain-rgb|raster
        """
        visualization = request.query_params.get("visualization")
        if visualization:
            value = visualization.strip().lower()
            if value in {"terrain", "terrain-rgb", "raster-dem"}:
                return True
            if value in {"raster", "rgb"}:
                return False

        for key in ("terrain", "raster_dem"):
            raw = request.query_params.get(key)
            if raw is None:
                continue

            value = raw.strip().lower()
            if value in {"1", "true", "yes", "on"}:
                return True
            if value in {"0", "false", "no", "off"}:
                return False

        return None
