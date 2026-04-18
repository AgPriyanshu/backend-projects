from dataclasses import dataclass

from pyproj import CRS
from rio_tiler.io import Reader
from rio_tiler.types import BBox

from .constants import FileFormat


def get_raster_kind(band_count: int) -> str:
    if band_count == 1:
        return "elevation"
    if band_count in (3, 4):
        return "ortho"
    return "raster"


@dataclass
class Resolution:
    x: int
    y: int


@dataclass
class RasterInfo:
    bounds: BBox
    band_count: int
    minzoom: int
    maxzoom: int
    crs: CRS
    resolution: Resolution


def get_raster_info(path: str) -> RasterInfo:
    with Reader(input=path, options={}) as cog:
        info = cog.info()
        x_res, y_res = cog.dataset.res  # type: ignore

        return {
            "bounds": info.bounds,
            "band_count": info.count,  # type: ignore
            "min_zoom": cog.minzoom,
            "max_zoom": cog.maxzoom,
            "crs": cog.crs,
            "resolution": Resolution(x_res, y_res),
        }


def format_to_ext(format: str):
    mapping = {
        FileFormat.GEOPACKAGE.value: "gpkg",
        FileFormat.SHAPEFILE.value: "shp",
        FileFormat.KML.value: "kml",
        FileFormat.GEOTIFF.value: "tif",
        FileFormat.COG.value: "tif",
    }

    return mapping.get(format, "dat")
