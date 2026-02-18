from django.db.models import TextChoices


class DatasetNodeType(TextChoices):
    FOLDER = "folder"
    DATASET = "dataset"


class DatasetType(TextChoices):
    VECTOR = "vector"
    RASTER = "raster"
    TEXT = "text"


class FileFormat(TextChoices):
    # Vector formats
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    KML = "kml"
    GEOPACKAGE = "gpkg"

    # Raster formats
    GEOTIFF = "geotiff"
    COG = "cog"
    PNG = "png"
    JPEG = "jpeg"

    # Document formats
    PDF = "pdf"
    TXT = "txt"


class TileSetStatus(TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DatasetStatus(TextChoices):
    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"
