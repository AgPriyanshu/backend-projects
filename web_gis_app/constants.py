from django.db.models import TextChoices

from shared.constants import BaseEnum


class DatasetNodeType(TextChoices):
    FOLDER = "folder"
    DATASET = "dataset"


class DatasetType(BaseEnum):
    VECTOR = "vector"
    RASTER = "raster"


class FileFormat(TextChoices):
    # Vector formats
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    KML = "kml"
    GEOPACKAGE = "gpkg"

    # Raster formats
    GEOTIFF = "geotiff"
    COG = "cog"  # Cloud Optimized GeoTIFF
    PNG = "png"
    JPEG = "jpeg"

    # Document formats
    PDF = "pdf"
