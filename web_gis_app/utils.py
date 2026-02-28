"""Utility functions for the web_gis_app module."""

from .constants import FileFormat

# Extension to format mapping (case-insensitive)
EXTENSION_TO_FORMAT = {
    # Vector formats.
    "shp": FileFormat.SHAPEFILE,
    "kml": FileFormat.KML,
    "gpkg": FileFormat.GEOPACKAGE,
    # Raster formats.
    "tif": FileFormat.GEOTIFF,
    "tiff": FileFormat.GEOTIFF,
    "cog": FileFormat.COG,
    "png": FileFormat.PNG,
    "jpg": FileFormat.JPEG,
    "jpeg": FileFormat.JPEG,
    # Text/Document formats.
    "pdf": FileFormat.PDF,
    "txt": FileFormat.TXT,
}


def detect_dataset_format(filename: str) -> str:
    """
    Format from filename extension.

    Args:
        filename: The name of the uploaded file

    Returns:
        file_format

    Raises:
        ValueError: If the file extension is not supported
    """

    if "." not in filename:
        raise ValueError(
            f"File '{filename}' has no extension. Unable to determine format."
        )

    extension = filename.rsplit(".", 1)[-1].lower()

    if extension not in EXTENSION_TO_FORMAT:
        supported_extensions = ", ".join(sorted(EXTENSION_TO_FORMAT.keys()))
        raise ValueError(
            f"Unsupported file extension '.{extension}'. "
            f"Supported extensions: {supported_extensions}"
        )

    file_format = EXTENSION_TO_FORMAT[extension]

    return file_format
