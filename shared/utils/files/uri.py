"""Utility functions for file path and URI parsing."""

import re
from typing import Optional, Union
from urllib.parse import urlparse

from .schemas import (
    AzureBlobComponents,
    AzureCustomComponents,
    HTTPComponents,
    LocalPathComponents,
    ParseURIResult,
    S3Components,
    URIType,
)


class URIParser:
    """Parser for identifying and extracting components from various URI types."""

    # Regex patterns for different URI types.
    S3_PATTERN = re.compile(r"^s3://([^/]+)/(.+)$")
    AZURE_BLOB_PATTERN = re.compile(r"^https://([^.]+)\.blob\.core\.windows\.net/(.+)$")
    AZURE_URI_PATTERN = re.compile(r"^azure://([^/]+)/(.+)$")
    HTTP_PATTERN = re.compile(r"^https?://")

    @staticmethod
    def identify_uri_type(path: str) -> URIType:
        """
        Identify the type of URI from a given path string.

        Args:
            path (str): The file path or URI to identify.

        Returns:
            URIType: The identified URI type (HTTP, HTTPS, S3, AZURE, LOCAL, or UNKNOWN).
        """
        if not isinstance(path, str) or not path.strip():
            return URIType.UNKNOWN

        path = path.strip()

        # Check S3.
        if URIParser.S3_PATTERN.match(path):
            return URIType.S3

        # Check Azure.
        if URIParser.AZURE_BLOB_PATTERN.match(
            path
        ) or URIParser.AZURE_URI_PATTERN.match(path):
            return URIType.AZURE

        # Check HTTP/HTTPS.
        if URIParser.HTTP_PATTERN.match(path):
            return URIType.HTTPS if path.startswith("https://") else URIType.HTTP

        # Check local path.
        if path.startswith(("/", ".", "~")) or re.match(r"^[a-zA-Z]:\\", path):
            return URIType.LOCAL

        return URIType.UNKNOWN

    @staticmethod
    def parse_s3_uri(uri: str) -> Optional[S3Components]:
        """
        Parse an S3 URI and extract bucket and key.

        Args:
            uri (str): S3 URI in format s3://bucket/key.

        Returns:
            Optional[S3Components]: Dictionary with 'bucket' and 'key' keys,
                or None if the URI is invalid.

        Example:
            >>> URIParser.parse_s3_uri("s3://my-bucket/path/to/file.txt")
            {'bucket': 'my-bucket', 'key': 'path/to/file.txt'}
        """
        match = URIParser.S3_PATTERN.match(uri)
        if match:
            return {"bucket": match.group(1), "key": match.group(2)}
        return None

    @staticmethod
    def parse_azure_uri(
        uri: str,
    ) -> Optional[Union[AzureBlobComponents, AzureCustomComponents]]:
        """
        Parse an Azure URI and extract container and blob name.

        Supports both Azure Blob Storage URLs (https://*.blob.core.windows.net)
        and azure:// scheme URIs.

        Args:
            uri (str): Azure URI.

        Returns:
            Optional[Union[AzureBlobComponents, AzureCustomComponents]]: Dictionary with extracted components,
                or None if the URI is invalid.

        Example:
            >>> URIParser.parse_azure_uri("https://myaccount.blob.core.windows.net/container/blob")
            {'account': 'myaccount', 'container': 'container', 'blob_name': 'blob'}
        """
        # Azure Blob Storage URL format.
        blob_match = URIParser.AZURE_BLOB_PATTERN.match(uri)
        if blob_match:
            account = blob_match.group(1)
            path_parts = blob_match.group(2).split("/", 1)
            container = path_parts[0]
            blob_name = path_parts[1] if len(path_parts) > 1 else ""
            return {
                "account": account,
                "container": container,
                "blob_name": blob_name,
            }

        # Azure custom URI format.
        azure_match = URIParser.AZURE_URI_PATTERN.match(uri)
        if azure_match:
            return {
                "container": azure_match.group(1),
                "blob_name": azure_match.group(2),
            }

        return None

    @staticmethod
    def parse_http_uri(uri: str) -> Optional[HTTPComponents]:
        """
        Parse an HTTP/HTTPS URI and extract components.

        Args:
            uri (str): HTTP(S) URI.

        Returns:
            Optional[HTTPComponents]: Dictionary with parsed URL components
                (scheme, netloc, path, params, query, fragment), or None if invalid.

        Example:
            >>> URIParser.parse_http_uri("https://example.com/path/to/file?key=value")
            {'scheme': 'https', 'netloc': 'example.com', 'path': '/path/to/file', ...}
        """
        if not URIParser.HTTP_PATTERN.match(uri):
            return None

        parsed = urlparse(uri)
        return {
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "fragment": parsed.fragment,
        }

    @staticmethod
    def parse_local_path(path: str) -> Optional[LocalPathComponents]:
        """
        Parse a local file path and extract directory and filename.

        Args:
            path (str): Local file path.

        Returns:
            Optional[LocalPathComponents]: Dictionary with 'directory' and 'filename' keys,
                or None if the path is invalid.

        Example:
            >>> URIParser.parse_local_path("/path/to/file.txt")
            {'directory': '/path/to', 'filename': 'file.txt'}
        """
        if not path:
            return None

        # Split the path into directory and filename.
        parts = path.rsplit("/", 1)
        if len(parts) == 2:
            directory, filename = parts
        else:
            directory = ""
            filename = parts[0]

        return {"directory": directory or ".", "filename": filename}

    @staticmethod
    def parse_uri(path: str) -> ParseURIResult:
        """
        Parse a URI/file path and return its type and components.

        This is the main entry point that identifies the URI type and calls
        the appropriate parser.

        Args:
            path (str): The file path or URI to parse.

        Returns:
            ParseURIResult: A dictionary containing:
                - 'type': URIType enum value
                - 'type_name': String name of the URI type
                - 'components': Parsed components specific to the URI type
                - 'original_path': The original input path
        """
        uri_type = URIParser.identify_uri_type(path)
        components = None

        if uri_type == URIType.S3:
            components = URIParser.parse_s3_uri(path)
        elif uri_type == URIType.AZURE:
            components = URIParser.parse_azure_uri(path)
        elif uri_type in (URIType.HTTP, URIType.HTTPS):
            components = URIParser.parse_http_uri(path)
        elif uri_type == URIType.LOCAL:
            components = URIParser.parse_local_path(path)

        return {
            "type": uri_type,
            "type_name": uri_type.value,
            "components": components,
            "original_path": path,
        }


def identify_uri_type(path: str) -> URIType:
    """
    Identify the type of URI from a given path string.

    Args:
        path (str): The file path or URI to identify.

    Returns:
        URIType: The identified URI type.
    """
    return URIParser.identify_uri_type(path)


def parse_uri(path: str) -> ParseURIResult:
    """
    Parse a URI/file path and return its type and components.

    Args:
        path (str): The file path or URI to parse.

    Returns:
        ParseURIResult: A dictionary with URI type and parsed components.
    """
    return URIParser.parse_uri(path)


def is_s3_uri(path: str) -> bool:
    """Check if a path is an S3 URI."""
    return identify_uri_type(path) == URIType.S3


def is_azure_uri(path: str) -> bool:
    """Check if a path is an Azure URI."""
    return identify_uri_type(path) == URIType.AZURE


def is_http_uri(path: str) -> bool:
    """Check if a path is an HTTP/HTTPS URI."""
    uri_type = identify_uri_type(path)
    return uri_type in (URIType.HTTP, URIType.HTTPS)


def is_local_path(path: str) -> bool:
    """Check if a path is a local file path."""
    return identify_uri_type(path) == URIType.LOCAL
