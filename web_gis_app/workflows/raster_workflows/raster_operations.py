from __future__ import annotations

import json
import os
from typing import Optional

import matplotlib.cm as cm
import numpy as np
import rasterio
from django.contrib.gis.geos import GEOSGeometry
from pydantic import Field
from rasterio.crs import CRS
from rasterio.mask import mask as rio_mask
from rasterio.warp import Resampling, reproject
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from shared.schemas import StrictPayload
from shared.workflows.base import Operation

from ...models import Feature, ProcessingJob
from ..helpers import create_staging_dataset, report_progress


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
        report_progress(self.ctx, 20, "Reading DEM...")

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

        report_progress(self.ctx, 50, "Computing hillshade...")

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

        shaded = np.sin(altitude_rad) * np.sin(slope) + np.cos(altitude_rad) * np.cos(
            slope
        ) * np.cos(azimuth_rad - aspect)
        shaded = np.clip(shaded * 255.0, 0, 255).astype("uint8")

        # Restore nodata areas as transparent (0).
        if nan_mask.shape == shaded.shape:
            shaded[nan_mask] = 0

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

        report_progress(self.ctx, 85, "Hillshade written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}


class SlopeOpPayload(_RasterOpPayloadBase):
    units: str = "degrees"
    z_factor: float = 1.0


class SlopeOp(Operation[SlopeOpPayload, dict]):
    """Compute slope GeoTIFF from a DEM."""

    name = "slope_op"

    def execute(self, *args, **kwargs) -> dict:
        report_progress(self.ctx, 20, "Reading DEM...")

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

        report_progress(self.ctx, 50, "Computing slope...")

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

        report_progress(self.ctx, 85, "Slope written")
        self.ctx["raster_output_path"] = output_path

        return {"output_path": output_path}


class ContourOpPayload(_RasterOpPayloadBase):
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

        report_progress(self.ctx, 20, "Reading DEM for contours...")

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

        report_progress(self.ctx, 50, "Tracing contour lines...")

        fig, ax = plt.subplots()
        contour_set = ax.contour(elevation, levels=levels)
        plt.close(fig)

        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

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

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 85, "Contours written")

        return {}


class ClipRasterOpPayload(_RasterOpPayloadBase):
    clip_dataset_id: Optional[str] = None
    clip_geometry: Optional[dict] = None


class ClipRasterOp(Operation[ClipRasterOpPayload, dict]):
    """Clip a raster by a GeoJSON polygon or by the union of a vector dataset."""

    name = "clip_raster_op"

    def execute(self, *args, **kwargs) -> dict:
        report_progress(self.ctx, 20, "Preparing clip geometry...")

        geoms = []

        if self.payload.clip_geometry:
            geoms = [shape(self.payload.clip_geometry)]
        elif self.payload.clip_dataset_id:
            features = Feature.objects.filter(dataset_id=self.payload.clip_dataset_id)
            geoms = [
                shape(json.loads(feature.geometry.geojson)) for feature in features
            ]

            if geoms:
                geoms = [unary_union(geoms)]
        else:
            raise ValueError("Either clip_dataset_id or clip_geometry is required.")

        report_progress(self.ctx, 40, "Clipping raster...")

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

        report_progress(self.ctx, 85, "Clipped raster written")
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

        report_progress(self.ctx, 20, "Reading input bands...")

        with rasterio.open(self.payload.input_path) as src:
            profile = src.profile.copy()
            variables = {}

            band_mapping = self.payload.band_mapping or {"A": 1}

            for var_name, band_index in band_mapping.items():
                variables[var_name] = src.read(band_index).astype("float32")

        report_progress(self.ctx, 50, "Evaluating expression...")

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

        report_progress(self.ctx, 85, "Result written")
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
                not isinstance(node.func, ast.Name) or node.func.id not in _whitelisted
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
                min(22, max(0, int(math.log2(360.0 / (res * 256))))) if res > 0 else 18
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
