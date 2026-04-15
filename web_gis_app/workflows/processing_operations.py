"""Operations used by geoprocessing workflows.

Organised as:
- Vector ops — run PostGIS SQL directly on the Feature model, no S3 round-trip.
- Raster ops — read/write GeoTIFF files using rasterio + numpy.
- CreateOutputDataset — shared finaliser: materialises the DatasetNode + Dataset
  (and TileSet for raster outputs) and links them back to the ProcessingJob.
"""

from __future__ import annotations

import os
from typing import Optional

from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from pydantic import Field

from shared.workflows.base.base_operation import Operation
from shared.workflows.schemas import StrictPayload

from ..constants import (
    DatasetNodeType,
    DatasetStatus,
    DatasetType,
    FileFormat,
    TileSetStatus,
)
from ..models import Dataset, DatasetNode, Feature, ProcessingJob, TileSet

# -- Shared output operation --


class CreateOutputDatasetPayload(StrictPayload):
    """Payload for the shared output dataset finaliser.

    For vector outputs: features are expected to be already written to PostGIS
    against `output_dataset_id`; this operation only finalises metadata.

    For raster outputs: `storage_path` points to the uploaded COG in object
    storage; this operation creates a TileSet pointing at it.
    """

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

        # Prefer metadata/file_size from ctx (written by ExtractRasterMetadata) over
        # the static payload values, which are empty when raster workflows are used.
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

            # Create with PENDING first so the post_save signal skips COG dispatch.
            dataset = Dataset.objects.create(
                dataset_node=dataset_node,
                type=self.payload.output_type,
                format=self.payload.output_format,
                metadata=metadata,
                file_name=f"{self.payload.output_name}.{self._ext_for_format()}",
                file_size=file_size,
                cloud_storage_path=self.payload.storage_path,
                status=DatasetStatus.PENDING,
            )

            if self.payload.output_type == DatasetType.RASTER.value:
                TileSet.objects.create(
                    dataset=dataset,
                    status=TileSetStatus.READY,
                    storage_path=self.payload.storage_path,
                    file_size=file_size,
                    bounds=metadata.get("bounds", []),
                    min_zoom=metadata.get("min_zoom", 0),
                    max_zoom=metadata.get("max_zoom", 22),
                )

            # Flip to UPLOADED now — signal fires but finds tileset.status==READY and skips COG task.
            dataset.status = DatasetStatus.UPLOADED
            dataset.save(update_fields=["status", "updated_at"])

            # Attach the pre-inserted features to this dataset, if any.
            pending_feature_dataset_id = self.ctx.get("pending_feature_dataset_id")

            if pending_feature_dataset_id:
                Feature.objects.filter(dataset_id=pending_feature_dataset_id).update(
                    dataset=dataset
                )

            job.output_dataset = dataset
            job.output_node = dataset_node
            job.save(update_fields=["output_dataset", "output_node", "updated_at"])

        return {
            "dataset_id": str(dataset.id),
            "dataset_node_id": str(dataset_node.id),
        }

    def _ext_for_format(self) -> str:
        mapping = {
            FileFormat.GEOPACKAGE.value: "gpkg",
            FileFormat.SHAPEFILE.value: "shp",
            FileFormat.KML.value: "kml",
            FileFormat.GEOTIFF.value: "tif",
            FileFormat.COG.value: "tif",
        }

        return mapping.get(self.payload.output_format, "dat")


# -- Vector operations --
#
# Vector ops write output features directly into the Feature table.  Because
# we need a dataset FK on Feature but the output Dataset doesn't exist yet,
# we use a placeholder approach: features are inserted with a throwaway
# "staging" dataset id recorded in ctx, and CreateOutputDataset rewires them
# once the real dataset is created.


class _VectorOpPayloadBase(StrictPayload):
    job_id: str
    input_dataset_id: str


def _materialise_staging_dataset(user) -> Dataset:
    """Create a transient Dataset + DatasetNode to temporarily hold output features."""

    node = DatasetNode.objects.create(
        name="__processing_staging__",
        type=DatasetNodeType.DATASET.value,
        user=user,
    )

    return Dataset.objects.create(
        dataset_node=node,
        type=DatasetType.VECTOR,
        format=FileFormat.GEOPACKAGE,
        file_name="staging.gpkg",
        file_size=0,
        cloud_storage_path="",
        status=DatasetStatus.PENDING,
    )


def _finalise_staging(ctx: dict, staging: Dataset) -> None:
    """Record staging dataset id in ctx so CreateOutputDataset can adopt its features."""

    ctx["pending_feature_dataset_id"] = str(staging.id)


def _report_progress(ctx: dict, progress: int, message: str = "") -> None:
    reporter = ctx.get("progress_reporter")

    if reporter is not None:
        reporter.report(progress, message)


class BufferOpPayload(_VectorOpPayloadBase):
    distance: float
    units: str = "meters"
    segments: int = 8


class BufferOp(Operation[BufferOpPayload, dict]):
    """Create a PostGIS buffer around every feature in the input dataset."""

    name = "buffer_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        distance_meters = self._to_meters(self.payload.distance, self.payload.units)

        _report_progress(self.ctx, 10, "Buffering features...")

        features = Feature.objects.filter(
            dataset_id=self.payload.input_dataset_id
        )
        total = features.count()

        if total == 0:
            _finalise_staging(self.ctx, staging)
            return {"feature_count": 0}

        batch = []

        for index, feature in enumerate(features.iterator()):
            buffered = self._buffer_geometry(feature.geometry, distance_meters)
            batch.append(
                Feature(
                    dataset=staging,
                    geometry=buffered,
                    properties=feature.properties,
                )
            )

            if len(batch) >= 500:
                Feature.objects.bulk_create(batch)
                batch = []

            if index % 50 == 0:
                _report_progress(
                    self.ctx,
                    10 + int(80 * (index + 1) / total),
                    f"Buffered {index + 1}/{total} features",
                )

        if batch:
            Feature.objects.bulk_create(batch)

        _finalise_staging(self.ctx, staging)

        return {"feature_count": total}

    @staticmethod
    def _to_meters(distance: float, units: str) -> float:
        if units == "kilometers":
            return distance * 1000
        if units == "degrees":
            # Rough conversion: 1 degree ~= 111 km at the equator.
            return distance * 111_000

        return distance

    @staticmethod
    def _buffer_geometry(geom, distance_meters: float):
        """Buffer a 4326 geometry using PostGIS via a raw SQL round-trip."""

        from django.db import connection

        srid = geom.srid or 4326

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT encode(ST_AsEWKB("
                "  ST_Buffer(ST_GeomFromEWKT(%s)::geography, %s)::geometry"
                "), 'hex')",
                [f"SRID={srid};{geom.wkt}", distance_meters],
            )
            row = cursor.fetchone()

        return GEOSGeometry(row[0])


class ClipVectorOpPayload(_VectorOpPayloadBase):
    clip_dataset_id: str


class ClipVectorOp(Operation[ClipVectorOpPayload, dict]):
    """Clip input features by the union of features in a clip dataset."""

    name = "clip_vector_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        _report_progress(self.ctx, 10, "Clipping features...")

        from django.db import connection

        # Insert intersection features directly via SQL for performance.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Multi(ST_Intersection(a.geometry, clip.geom)),
                    a.properties,
                    NOW(),
                    NOW()
                FROM feature a
                CROSS JOIN (
                    SELECT ST_Union(geometry) AS geom FROM feature WHERE dataset_id = %s
                ) AS clip
                WHERE a.dataset_id = %s
                  AND ST_Intersects(a.geometry, clip.geom)
                  AND NOT ST_IsEmpty(ST_Intersection(a.geometry, clip.geom))
                """,
                [
                    str(staging.id),
                    self.payload.clip_dataset_id,
                    self.payload.input_dataset_id,
                ],
            )

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 90, "Clip complete")

        return {}


class DissolveOpPayload(_VectorOpPayloadBase):
    dissolve_field: Optional[str] = None


class DissolveOp(Operation[DissolveOpPayload, dict]):
    """Merge features via ST_Union, optionally grouped by a properties field."""

    name = "dissolve_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        _report_progress(self.ctx, 10, "Dissolving features...")

        if Feature.objects.filter(dataset_id=self.payload.input_dataset_id).count() == 0:
            _finalise_staging(self.ctx, staging)
            return {"feature_count": 0}

        from django.db import connection

        if self.payload.dissolve_field:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_Multi(ST_Union(geometry)),
                        jsonb_build_object(%s, properties->>%s),
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    GROUP BY properties->>%s
                    HAVING ST_Union(geometry) IS NOT NULL
                    """,
                    [
                        str(staging.id),
                        self.payload.dissolve_field,
                        self.payload.dissolve_field,
                        self.payload.input_dataset_id,
                        self.payload.dissolve_field,
                    ],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_Multi(ST_Union(geometry)),
                        '{}'::jsonb,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    HAVING ST_Union(geometry) IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 90, "Dissolve complete")

        return {}


class CentroidOpPayload(_VectorOpPayloadBase):
    pass


class CentroidOp(Operation[CentroidOpPayload, dict]):
    """Compute a centroid point for every feature."""

    name = "centroid_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        _report_progress(self.ctx, 10, "Computing centroids...")

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Centroid(geometry),
                    properties,
                    NOW(),
                    NOW()
                FROM feature
                WHERE dataset_id = %s
                """,
                [str(staging.id), self.payload.input_dataset_id],
            )

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 90, "Centroid complete")

        return {}


class SimplifyOpPayload(_VectorOpPayloadBase):
    tolerance: float


class SimplifyOp(Operation[SimplifyOpPayload, dict]):
    """Apply ST_Simplify to every feature geometry."""

    name = "simplify_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        _report_progress(self.ctx, 10, "Simplifying geometries...")

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Simplify(geometry, %s),
                    properties,
                    NOW(),
                    NOW()
                FROM feature
                WHERE dataset_id = %s
                  AND ST_Simplify(geometry, %s) IS NOT NULL
                """,
                [
                    str(staging.id),
                    self.payload.tolerance,
                    self.payload.input_dataset_id,
                    self.payload.tolerance,
                ],
            )

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 90, "Simplify complete")

        return {}


class ConvexHullOpPayload(_VectorOpPayloadBase):
    per_feature: bool = False


class ConvexHullOp(Operation[ConvexHullOpPayload, dict]):
    """Compute a convex hull, either per feature or as a single hull over all features."""

    name = "convex_hull_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        _report_progress(self.ctx, 10, "Computing convex hull...")

        if Feature.objects.filter(dataset_id=self.payload.input_dataset_id).count() == 0:
            _finalise_staging(self.ctx, staging)
            return {"feature_count": 0}

        from django.db import connection

        if self.payload.per_feature:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_ConvexHull(geometry),
                        properties,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                      AND geometry IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_ConvexHull(ST_Collect(geometry)),
                        '{}'::jsonb,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    HAVING ST_ConvexHull(ST_Collect(geometry)) IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 90, "Convex hull complete")

        return {}


# -- Raster operations --


class _RasterOpPayloadBase(StrictPayload):
    job_id: str
    input_path: str
    work_dir: str


class HillshadeOpPayload(_RasterOpPayloadBase):
    azimuth: float = 315.0
    altitude: float = 45.0
    z_factor: float = 1.0


class HillshadeOp(Operation[HillshadeOpPayload, dict]):
    """Compute a hillshade GeoTIFF from a DEM."""

    name = "hillshade_op"

    def execute(self, *args, **kwargs) -> dict:
        import numpy as np
        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import Resampling, reproject

        _report_progress(self.ctx, 20, "Reading DEM...")

        with rasterio.open(self.payload.input_path) as src:
            nodata = src.nodata
            profile = src.profile.copy()
            crs = src.crs

            # Reproject to a metric CRS so gradient units match elevation units.
            if crs and crs.is_geographic:
                from rasterio.warp import calculate_default_transform

                dst_crs = CRS.from_epsg(3857)
                transform, width, height = calculate_default_transform(
                    crs, dst_crs, src.width, src.height, *src.bounds
                )
                metric_data = np.empty((height, width), dtype="float32")
                reproject(
                    source=rasterio.band(src, 1),
                    destination=metric_data,
                    src_transform=src.transform,
                    src_crs=crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                    src_nodata=nodata,
                    dst_nodata=np.nan,
                )
                elevation = metric_data
                xres = transform.a
                yres = abs(transform.e)
                profile.update(
                    crs=dst_crs, transform=transform, width=width, height=height
                )
            else:
                elevation = src.read(1).astype("float32")
                xres, yres = src.res

                if nodata is not None:
                    elevation = np.where(elevation == nodata, np.nan, elevation)

        _report_progress(self.ctx, 50, "Computing hillshade...")

        # Fill small NaN gaps with interpolated values so the gradient is smooth.
        nan_mask = np.isnan(elevation)

        if nan_mask.any():
            from scipy.ndimage import generic_filter

            def _fill_nan(values):
                center = values[len(values) // 2]
                if np.isnan(center):
                    valid = values[~np.isnan(values)]
                    return float(np.mean(valid)) if len(valid) > 0 else 0.0
                return center

            elevation = generic_filter(elevation, _fill_nan, size=3)

        azimuth_rad = np.deg2rad(360.0 - self.payload.azimuth + 90.0)
        altitude_rad = np.deg2rad(self.payload.altitude)

        dz_dx, dz_dy = np.gradient(elevation * self.payload.z_factor, xres, yres)
        slope = np.pi / 2.0 - np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))
        aspect = np.arctan2(-dz_dx, dz_dy)

        shaded = (
            np.sin(altitude_rad) * np.sin(slope)
            + np.cos(altitude_rad) * np.cos(slope) * np.cos(azimuth_rad - aspect)
        )
        shaded = np.clip(shaded * 255.0, 0, 255).astype("uint8")

        # Restore nodata areas as transparent (0).
        if nan_mask.shape == shaded.shape:
            shaded[nan_mask] = 0

        # Apply a terrain colormap (brown-grey) and output RGBA so MapLibre renders it correctly.
        import matplotlib.cm as cm

        norm = shaded.astype("float32") / 255.0
        colormap = cm.get_cmap("terrain")
        rgba = (colormap(norm) * 255).astype("uint8")  # shape: (H, W, 4)

        # Mark nodata pixels as fully transparent.
        if nan_mask.shape == shaded.shape:
            rgba[nan_mask, 3] = 0

        output_path = os.path.join(self.payload.work_dir, "output.tif")
        profile.update(dtype="uint8", count=4, compress="lzw")
        profile.pop("nodata", None)

        with rasterio.open(output_path, "w", **profile) as dst:
            for i in range(4):
                dst.write(rgba[:, :, i], i + 1)

        _report_progress(self.ctx, 85, "Hillshade written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}


class SlopeOpPayload(_RasterOpPayloadBase):
    units: str = "degrees"
    z_factor: float = 1.0


class SlopeOp(Operation[SlopeOpPayload, dict]):
    """Compute slope GeoTIFF from a DEM."""

    name = "slope_op"

    def execute(self, *args, **kwargs) -> dict:
        import matplotlib.cm as cm
        import numpy as np
        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import Resampling, reproject

        _report_progress(self.ctx, 20, "Reading DEM...")

        with rasterio.open(self.payload.input_path) as src:
            nodata = src.nodata
            profile = src.profile.copy()
            crs = src.crs

            if crs and crs.is_geographic:
                from rasterio.warp import calculate_default_transform

                dst_crs = CRS.from_epsg(3857)
                transform, width, height = calculate_default_transform(
                    crs, dst_crs, src.width, src.height, *src.bounds
                )
                metric_data = np.empty((height, width), dtype="float32")
                reproject(
                    source=rasterio.band(src, 1),
                    destination=metric_data,
                    src_transform=src.transform,
                    src_crs=crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                    src_nodata=nodata,
                    dst_nodata=np.nan,
                )
                elevation = metric_data
                xres = transform.a
                yres = abs(transform.e)
                profile.update(
                    crs=dst_crs, transform=transform, width=width, height=height
                )
            else:
                elevation = src.read(1).astype("float32")
                xres, yres = src.res

                if nodata is not None:
                    elevation = np.where(elevation == nodata, np.nan, elevation)

        nan_mask = np.isnan(elevation)
        elevation_filled = np.where(nan_mask, 0.0, elevation)

        _report_progress(self.ctx, 50, "Computing slope...")

        dz_dx, dz_dy = np.gradient(elevation_filled * self.payload.z_factor, xres, yres)
        slope_rad = np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))

        if self.payload.units == "percent":
            slope_values = np.tan(slope_rad) * 100.0
            vmax = 100.0
        else:
            slope_values = np.rad2deg(slope_rad)
            vmax = 90.0

        slope_values[nan_mask] = np.nan

        # Normalise 0→vmax and apply viridis colormap, output RGBA.
        valid_slope = slope_values[~nan_mask]
        s_min = float(np.nanmin(valid_slope)) if valid_slope.size > 0 else 0.0
        s_max = float(np.nanmax(valid_slope)) if valid_slope.size > 0 else vmax
        s_max = s_max if s_max > s_min else s_min + 1.0

        norm = np.clip((slope_values - s_min) / (s_max - s_min), 0.0, 1.0)
        norm = np.where(nan_mask, 0.0, norm)

        colormap = cm.get_cmap("viridis")
        rgba = (colormap(norm) * 255).astype("uint8")
        rgba[nan_mask, 3] = 0

        output_path = os.path.join(self.payload.work_dir, "output.tif")
        profile.update(dtype="uint8", count=4, compress="lzw")
        profile.pop("nodata", None)

        with rasterio.open(output_path, "w", **profile) as dst:
            for i in range(4):
                dst.write(rgba[:, :, i], i + 1)

        _report_progress(self.ctx, 85, "Slope written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}


class ContourOpPayload(_RasterOpPayloadBase):
    job_id: str
    interval: float
    attribute_name: str = "elevation"


class ContourOp(Operation[ContourOpPayload, dict]):
    """Extract contour lines from a DEM and write them as PostGIS features."""

    name = "contour_op"

    def execute(self, *args, **kwargs) -> dict:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import rasterio
        from rasterio.transform import xy
        from shapely.geometry import LineString

        _report_progress(self.ctx, 20, "Reading DEM for contours...")

        with rasterio.open(self.payload.input_path) as src:
            elevation = src.read(1).astype("float32")
            transform = src.transform
            nodata = src.nodata
            src_crs = src.crs

        if nodata is not None:
            elevation = np.where(elevation == nodata, np.nan, elevation)

        # Build a transformer to project raster coords -> 4326 (lng, lat).
        from pyproj import Transformer

        if src_crs and src_crs.to_string() != "EPSG:4326":
            to_4326 = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
        else:
            to_4326 = None

        z_min = np.nanmin(elevation)
        z_max = np.nanmax(elevation)
        levels = np.arange(
            np.floor(z_min / self.payload.interval) * self.payload.interval,
            z_max + self.payload.interval,
            self.payload.interval,
        )

        _report_progress(self.ctx, 50, "Tracing contour lines...")

        fig, ax = plt.subplots()
        contour_set = ax.contour(elevation, levels=levels)
        plt.close(fig)

        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = _materialise_staging_dataset(job.user)

        features_batch = []

        for level_index, segments in enumerate(contour_set.allsegs):
            elev_value = float(contour_set.levels[level_index])

            for segment in segments:
                if len(segment) < 2:
                    continue

                coords = [xy(transform, pt[1], pt[0]) for pt in segment]

                if to_4326 is not None:
                    coords = [to_4326.transform(x, y) for x, y in coords]

                line = LineString(coords)
                features_batch.append(
                    Feature(
                        dataset=staging,
                        geometry=GEOSGeometry(line.wkt, srid=4326),
                        properties={self.payload.attribute_name: elev_value},
                    )
                )

                if len(features_batch) >= 500:
                    Feature.objects.bulk_create(features_batch)
                    features_batch = []

        if features_batch:
            Feature.objects.bulk_create(features_batch)

        _finalise_staging(self.ctx, staging)
        _report_progress(self.ctx, 85, "Contours written")

        return {}


class ClipRasterOpPayload(_RasterOpPayloadBase):
    clip_dataset_id: Optional[str] = None
    clip_geometry: Optional[dict] = None


class ClipRasterOp(Operation[ClipRasterOpPayload, dict]):
    """Clip a raster by a GeoJSON polygon or by the union of a vector dataset."""

    name = "clip_raster_op"

    def execute(self, *args, **kwargs) -> dict:
        import rasterio
        from rasterio.mask import mask as rio_mask
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union

        _report_progress(self.ctx, 20, "Preparing clip geometry...")

        geoms = []

        if self.payload.clip_geometry:
            geoms = [shape(self.payload.clip_geometry)]
        elif self.payload.clip_dataset_id:
            features = Feature.objects.filter(
                dataset_id=self.payload.clip_dataset_id
            )
            import json
            geoms = [shape(json.loads(feature.geometry.geojson)) for feature in features]

            if geoms:
                geoms = [unary_union(geoms)]
        else:
            raise ValueError("Either clip_dataset_id or clip_geometry is required.")

        _report_progress(self.ctx, 40, "Clipping raster...")

        with rasterio.open(self.payload.input_path) as src:
            clipped, clipped_transform = rio_mask(
                src, [mapping(g) for g in geoms], crop=True
            )
            profile = src.profile.copy()

        profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=clipped_transform,
            compress="lzw",
        )

        output_path = os.path.join(self.payload.work_dir, "output.tif")

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(clipped)

        _report_progress(self.ctx, 85, "Clipped raster written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}


class RasterCalcOpPayload(_RasterOpPayloadBase):
    expression: str
    band_mapping: dict = Field(default_factory=dict)


class RasterCalcOp(Operation[RasterCalcOpPayload, dict]):
    """Evaluate a safe math expression across raster bands.

    `band_mapping` maps variable names to 1-based band indices, e.g.
    {"A": 1, "B": 2}. The expression is evaluated with numpy and
    strictly restricted to arithmetic/boolean ops.
    """

    name = "raster_calc_op"

    def execute(self, *args, **kwargs) -> dict:
        import numpy as np
        import rasterio

        allowed_names = {
            "abs": np.abs,
            "sqrt": np.sqrt,
            "log": np.log,
            "exp": np.exp,
            "min": np.minimum,
            "max": np.maximum,
        }

        _report_progress(self.ctx, 20, "Reading input bands...")

        with rasterio.open(self.payload.input_path) as src:
            profile = src.profile.copy()
            variables = {}

            band_mapping = self.payload.band_mapping or {"A": 1}

            for var_name, band_index in band_mapping.items():
                variables[var_name] = src.read(band_index).astype("float32")

        _report_progress(self.ctx, 50, "Evaluating expression...")

        self._assert_safe_expression(self.payload.expression)

        safe_globals: dict = {"__builtins__": {}}
        safe_globals.update(allowed_names)
        safe_globals.update(variables)
        result = eval(self.payload.expression, safe_globals, {})  # noqa: S307 - inputs are pre-validated.

        result = np.asarray(result, dtype="float32")

        output_path = os.path.join(self.payload.work_dir, "output.tif")
        profile.update(count=1, dtype="float32", compress="lzw")

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(result, 1)

        _report_progress(self.ctx, 85, "Result written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}

    @staticmethod
    def _assert_safe_expression(expression: str) -> None:
        import ast

        # ast.Num was removed in Python 3.12 — ast.Constant covers numeric literals.
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Name,
            ast.Load,
            ast.Call,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Pow,
            ast.Mod,
            ast.USub,
            ast.UAdd,
            ast.FloorDiv,
            ast.BitAnd,
            ast.BitOr,
            ast.BitXor,
            ast.BoolOp,
            ast.And,
            ast.Or,
            ast.Compare,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
        )

        tree = ast.parse(expression, mode="eval")

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(
                    f"Expression contains disallowed node: {type(node).__name__}."
                )

            _whitelisted = {"abs", "sqrt", "log", "exp", "min", "max"}

            if isinstance(node, ast.Call) and (
                not isinstance(node.func, ast.Name)
                or node.func.id not in _whitelisted
            ):
                raise ValueError("Only whitelisted functions may be called.")


# -- Raster output metadata extraction --
#
# Runs after the raster op but before upload so we can enrich the output
# dataset metadata (bounds, zoom levels, band count).


class ExtractRasterMetadataPayload(StrictPayload):
    path: str


class ExtractRasterMetadata(Operation[ExtractRasterMetadataPayload, dict]):
    """Extract bounds / zoom / band metadata from the output raster.

    Also converts the file to a Cloud Optimized GeoTIFF (COG) with overviews
    in-place so that rio-tiler can serve tiles efficiently without reading the
    full-resolution data at every zoom level.
    """

    name = "extract_raster_metadata"

    def execute(self, *args, **kwargs) -> dict:
        import math

        import rasterio
        from rasterio.warp import transform_bounds

        path = self.payload.path
        self._build_cog(path)

        with rasterio.open(path) as src:
            src_crs = src.crs

            if src_crs and src_crs.to_string() != "EPSG:4326":
                bounds = list(transform_bounds(src_crs, "EPSG:4326", *src.bounds))
            else:
                bounds = list(src.bounds)

            res = src.res[0]
            max_zoom = (
                min(22, max(0, int(math.log2(360.0 / (res * 256)))))
                if res > 0
                else 18
            )
            band_count = src.count

        file_size = os.path.getsize(path)

        metadata = {
            "bounds": bounds,
            "min_zoom": max(0, max_zoom - 10),
            "max_zoom": max_zoom,
            "band_count": band_count,
        }

        self.ctx["raster_output_metadata"] = metadata
        self.ctx["raster_output_file_size"] = file_size

        return metadata

    @staticmethod
    def _build_cog(path: str) -> None:
        """Convert the file at `path` to a COG with overviews in-place."""
        import shutil
        import tempfile

        from rio_cogeo.cogeo import cog_translate
        from rio_cogeo.profiles import cog_profiles

        tmp = tempfile.mktemp(suffix=".tif", prefix="cog_")

        try:
            cog_translate(
                path,
                tmp,
                cog_profiles.get("deflate"),
                overview_resampling="nearest",
                quiet=True,
            )
            shutil.move(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
