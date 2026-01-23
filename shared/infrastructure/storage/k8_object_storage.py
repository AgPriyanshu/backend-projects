import io
import os
from typing import Any, BinaryIO, Dict, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .base import ObjectStorageAbstract


class K8sObjectStorage(ObjectStorageAbstract):
    """
    Kubernetes object storage implementation using boto3 with SeaweedFS.
    Configuration is loaded from environment variables.
    """

    def __init__(self):
        """Initialize boto3 S3 client for SeaweedFS from environment variables."""
        # Get environment variables with error checking
        try:
            endpoint = os.environ["S3_ENDPOINT"]
            access_key = os.environ["S3_ACCESS_KEY"]
            secret_key = os.environ["S3_SECRET_KEY"]
            region = os.environ["S3_REGION"]
            self.default_bucket = os.environ["S3_BUCKET"]
        except KeyError as e:
            raise RuntimeError(
                f"Missing required environment variable: {e}. "
                "Please ensure all S3 configuration variables are set in your .env file."
            )

        if not self.default_bucket:
            raise RuntimeError("S3_BUCKET environment variable is empty")

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def upload_object(
        self,
        file: BinaryIO,
        key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload an object to S3-compatible storage."""
        # Use default bucket if not specified
        upload_bucket = bucket if bucket is not None else self.default_bucket

        try:
            # Ensure bucket exists
            try:
                self.client.head_bucket(Bucket=upload_bucket)
            except ClientError:
                self.client.create_bucket(Bucket=upload_bucket)

            # Get file size
            file.seek(0, io.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            upload_bucket = bucket or self.default_bucket

            # Upload object
            response = self.client.put_object(
                Bucket=upload_bucket,
                Key=key,
                Body=file,
                Metadata=metadata or {},
            )

            return {
                "bucket": upload_bucket,
                "key": key,
                "etag": response.get("ETag", "").strip('"'),
                "version_id": response.get("VersionId"),
                "size": file_size,
            }
        except ClientError as e:
            raise RuntimeError(f"Failed to upload object: {e}")

    def download_object(self, bucket: str, key: str) -> BinaryIO:
        """Download an object from S3-compatible storage."""
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)

            # Read the response body into a BytesIO object
            data = io.BytesIO(response["Body"].read())

            # Reset to beginning for reading
            data.seek(0)
            return data
        except ClientError as e:
            raise RuntimeError(f"Failed to download object: {e}")

    def get_object_info(self, bucket: str, key: str) -> Dict[str, Any]:
        """Get object metadata from S3-compatible storage."""
        try:
            response = self.client.head_object(Bucket=bucket, Key=key)

            return {
                "bucket": bucket,
                "key": key,
                "size": response.get("ContentLength"),
                "etag": response.get("ETag", "").strip('"'),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified").isoformat()
                if response.get("LastModified")
                else None,
                "metadata": response.get("Metadata", {}),
                "version_id": response.get("VersionId"),
            }
        except ClientError as e:
            raise RuntimeError(f"Failed to get object info: {e}")

    def generate_presigned_url(
        self, bucket: str, key: str, expiration: int = 3600, method: str = "GET"
    ) -> str:
        """Generate a presigned URL for S3-compatible storage object."""
        try:
            method_upper = method.upper()
            if method_upper == "GET":
                client_method = "get_object"
            elif method_upper == "PUT":
                client_method = "put_object"
            else:
                raise ValueError(f"Unsupported method: {method}. Use 'GET' or 'PUT'")

            url = self.client.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiration,
            )

            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    def delete_object(self, bucket: str, key: str) -> bool:
        """Delete an object from S3-compatible storage."""
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to delete object: {e}")

    def list_objects(
        self, bucket: str, prefix: Optional[str] = None, max_results: int = 1000
    ) -> list[Dict[str, Any]]:
        """List objects in an S3-compatible storage bucket."""
        try:
            objects = []
            continuation_token = None

            while len(objects) < max_results:
                # Prepare list_objects_v2 parameters
                params = {
                    "Bucket": bucket,
                    "MaxKeys": min(max_results - len(objects), 1000),
                }
                if prefix:
                    params["Prefix"] = prefix
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                # List objects
                response = self.client.list_objects_v2(**params)

                # Process contents
                for obj in response.get("Contents", []):
                    objects.append(
                        {
                            "key": obj.get("Key"),
                            "size": obj.get("Size"),
                            "etag": obj.get("ETag", "").strip('"'),
                            "last_modified": obj.get("LastModified").isoformat()
                            if obj.get("LastModified")
                            else None,
                            "storage_class": obj.get("StorageClass"),
                        }
                    )

                # Check if there are more results
                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

            return objects
        except ClientError as e:
            raise RuntimeError(f"Failed to list objects: {e}")
