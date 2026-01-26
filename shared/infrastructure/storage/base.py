from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Dict, Optional


class ObjectStorageAbstract(ABC):
    """Abstract base class for object storage implementations across different cloud providers."""

    @abstractmethod
    def __init__(self):
        """Initialize the storage client. Subclasses should set up their client here."""

    @abstractmethod
    def upload_object(
        self,
        file: BinaryIO,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload an object to storage.

        Args:
            file: File-like object to upload
            bucket: Bucket/container name
            key: Object key/path
            metadata: Optional metadata to attach to the object

        Returns:
            Dict containing upload result information
        """
        raise NotImplementedError

    @abstractmethod
    def download_object(self, key: str, bucket: Optional[str] = None) -> BinaryIO:
        """
        Download an object from storage.

        Args:
            key: Object key/path
            bucket: Optional bucket/container name (uses default if not specified)

        Returns:
            File-like object containing the downloaded data
        """
        raise NotImplementedError

    @abstractmethod
    def get_object_info(self, key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata and information about an object.

        Args:
            key: Object key/path
            bucket: Optional bucket/container name (uses default if not specified)

        Returns:
            Dict containing object metadata
        """
        raise NotImplementedError

    @abstractmethod
    def generate_presigned_url(
        self, key: str, bucket: Optional[str] = None, expiration: int = 3600, method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for temporary access to an object.

        Args:
            key: Object key/path
            bucket: Optional bucket/container name (uses default if not specified)
            expiration: URL expiration time in seconds
            method: HTTP method (GET, PUT, etc.)

        Returns:
            Presigned URL string
        """
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, key: str, bucket: Optional[str] = None) -> bool:
        """
        Delete an object from storage.

        Args:
            key: Object key/path
            bucket: Optional bucket/container name (uses default if not specified)

        Returns:
            True if deletion was successful
        """
        raise NotImplementedError

    @abstractmethod
    def list_objects(
        self, prefix: Optional[str] = None, bucket: Optional[str] = None, max_results: int = 1000
    ) -> list[Dict[str, Any]]:
        """
        List objects in a bucket.

        Args:
            prefix: Optional prefix to filter objects
            bucket: Optional bucket/container name (uses default if not specified)
            max_results: Maximum number of results to return

        Returns:
            List of object metadata dictionaries
        """
        raise NotImplementedError
