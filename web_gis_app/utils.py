"""Utility functions for the web_gis_app module."""

from .constants import DatasetType, FileFormat

# Extension to format mapping (case-insensitive)
EXTENSION_TO_FORMAT = {
    # Vector formats
    "geojson": FileFormat.GEOJSON,
    "shp": FileFormat.SHAPEFILE,
    "kml": FileFormat.KML,
    "gpkg": FileFormat.GEOPACKAGE,
    # Raster formats
    "tif": FileFormat.GEOTIFF,
    "tiff": FileFormat.GEOTIFF,
    "cog": FileFormat.COG,
    "png": FileFormat.PNG,
    "jpg": FileFormat.JPEG,
    "jpeg": FileFormat.JPEG,
    # Text/Document formats
    "pdf": FileFormat.PDF,
    "txt": FileFormat.TXT,
}

# Extension to dataset type mapping
EXTENSION_TO_TYPE = {
    # Vector formats
    "geojson": DatasetType.VECTOR,
    "shp": DatasetType.VECTOR,
    "kml": DatasetType.VECTOR,
    "gpkg": DatasetType.VECTOR,
    # Raster formats
    "tif": DatasetType.RASTER,
    "tiff": DatasetType.RASTER,
    "cog": DatasetType.RASTER,
    "png": DatasetType.RASTER,
    "jpg": DatasetType.RASTER,
    "jpeg": DatasetType.RASTER,
    # Text/Document formats
    "pdf": DatasetType.TEXT,
    "txt": DatasetType.TEXT,
}


def detect_dataset_info(filename: str) -> tuple[str, str]:
    """
    Detect dataset type and format from filename extension.

    Args:
        filename: The name of the uploaded file

    Returns:
        Tuple of (dataset_type, file_format)

    Raises:
        ValueError: If the file extension is not supported
    """
    # Extract extension (case-insensitive)
    if "." not in filename:
        raise ValueError(
            f"File '{filename}' has no extension. Unable to determine format."
        )

    extension = filename.rsplit(".", 1)[-1].lower()

    # Check if extension is supported
    if extension not in EXTENSION_TO_FORMAT:
        supported_extensions = ", ".join(sorted(EXTENSION_TO_FORMAT.keys()))
        raise ValueError(
            f"Unsupported file extension '.{extension}'. "
            f"Supported extensions: {supported_extensions}"
        )

    dataset_type = EXTENSION_TO_TYPE[extension]
    file_format = EXTENSION_TO_FORMAT[extension]

    return dataset_type, file_format
