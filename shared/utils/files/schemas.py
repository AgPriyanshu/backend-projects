from enum import StrEnum
from typing import Optional, TypedDict, Union


class S3Components(TypedDict):
    """Components extracted from an S3 URI."""

    bucket: str
    key: str


class AzureBlobComponents(TypedDict):
    """Components extracted from an Azure Blob Storage URI."""

    account: str
    container: str
    blob_name: str


class AzureCustomComponents(TypedDict):
    """Components extracted from a custom azure:// URI."""

    container: str
    blob_name: str


class HTTPComponents(TypedDict):
    """Components extracted from an HTTP/HTTPS URI."""

    scheme: str
    netloc: str
    path: str
    params: str
    query: str
    fragment: str


class LocalPathComponents(TypedDict):
    """Components extracted from a local file path."""

    directory: str
    filename: str


class ParseURIResult(TypedDict):
    """Result of parsing a URI/file path."""

    type: "URIType"
    type_name: str
    components: Optional[
        Union[
            S3Components,
            AzureBlobComponents,
            AzureCustomComponents,
            HTTPComponents,
            LocalPathComponents,
        ]
    ]
    original_path: str


class URIType(StrEnum):
    """Enumeration of supported URI types."""

    HTTP = "http"
    HTTPS = "https"
    S3 = "s3"
    AZURE = "azure"
    LOCAL = "local"
    UNKNOWN = "unknown"
