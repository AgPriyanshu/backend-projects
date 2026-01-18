from shared.constants import BaseEnum


class DatasetNodeType(BaseEnum):
    Folder = "folder"
    Dataset = "dataset"


class DatasetType(BaseEnum):
    Vector = "vector"
    Raster = "raster"
    GeoPDF = "geo_pdf"
    Document = "document"


class FileFormat(BaseEnum):
    # Vector formats
    GeoJSON = "geojson"
    Shapefile = "shapefile"
    KML = "kml"
    GeoPackage = "gpkg"

    # Raster formats
    GeoTIFF = "geotiff"
    COG = "cog"  # Cloud Optimized GeoTIFF
    PNG = "png"
    JPEG = "jpeg"

    # Document formats
    PDF = "pdf"
