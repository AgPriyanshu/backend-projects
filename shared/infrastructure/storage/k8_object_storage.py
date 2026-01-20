import io
import os
from datetime import timedelta
from typing import Any, BinaryIO, Dict, Optional

from minio import Minio
from minio.error import S3Error

from .base import ObjectStorageAbstract


class K8sObjectStorage(ObjectStorageAbstract):
    """
    Kubernetes object storage implementation using MinIO or S3-compatible storage.
    Configuration is loaded from environment variables.
    """

    def __init__(self):
        """Initialize MinIO client from environment variables."""
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

        # Determine if we should use secure connection (HTTPS)
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        # Initialize MinIO client
        self.client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

    def upload_object(
        self,
        file: BinaryIO,
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload an object to MinIO storage."""
        try:
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)

            # Get file size
            file.seek(0, io.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            # Upload object
            result = self.client.put_object(
                bucket, key, file, length=file_size, metadata=metadata or {}
            )

            return {
                "bucket": result.bucket_name,
                "key": result.object_name,
                "etag": result.etag,
                "version_id": result.version_id,
                "size": file_size,
            }
        except S3Error as e:
            raise RuntimeError(f"Failed to upload object: {e}")

    def download_object(self, bucket: str, key: str) -> BinaryIO:
        """Download an object from MinIO storage."""
        try:
            response = self.client.get_object(bucket, key)

            # Read the response into a BytesIO object
            data = io.BytesIO(response.read())
            response.close()
            response.release_conn()

            # Reset to beginning for reading
            data.seek(0)
            return data
        except S3Error as e:
            raise RuntimeError(f"Failed to download object: {e}")

    def get_object_info(self, bucket: str, key: str) -> Dict[str, Any]:
        """Get object metadata from MinIO."""
        try:
            stat = self.client.stat_object(bucket, key)

            return {
                "bucket": stat.bucket_name,
                "key": stat.object_name,
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified.isoformat()
                if stat.last_modified
                else None,
                "metadata": stat.metadata,
                "version_id": stat.version_id,
            }
        except S3Error as e:
            raise RuntimeError(f"Failed to get object info: {e}")

    def generate_presigned_url(
        self, bucket: str, key: str, expiration: int = 3600, method: str = "GET"
    ) -> str:
        """Generate a presigned URL for MinIO object."""
        try:
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket, key, expires=timedelta(seconds=expiration)
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket, key, expires=timedelta(seconds=expiration)
                )
            else:
                raise ValueError(f"Unsupported method: {method}. Use 'GET' or 'PUT'")

            return url
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    def delete_object(self, bucket: str, key: str) -> bool:
        """Delete an object from MinIO."""
        try:
            self.client.remove_object(bucket, key)
            return True
        except S3Error as e:
            raise RuntimeError(f"Failed to delete object: {e}")

    def list_objects(
        self, bucket: str, prefix: Optional[str] = None, max_results: int = 1000
    ) -> list[Dict[str, Any]]:
        """List objects in a MinIO bucket."""
        try:
            objects = []

            # List objects with optional prefix
            for obj in self.client.list_objects(
                bucket, prefix=prefix or "", recursive=True
            ):
                objects.append(
                    {
                        "key": obj.object_name,
                        "size": obj.size,
                        "etag": obj.etag,
                        "last_modified": obj.last_modified.isoformat()
                        if obj.last_modified
                        else None,
                        "is_dir": obj.is_dir,
                        "content_type": obj.content_type,
                        "metadata": obj.metadata,
                    }
                )

                # Limit results
                if len(objects) >= max_results:
                    break

            return objects
        except S3Error as e:
            raise RuntimeError(f"Failed to list objects: {e}")
