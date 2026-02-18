import io
import os
from typing import Any, BinaryIO, Dict, Optional

import boto3
from botocore import UNSIGNED
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
        # Get environment variables
        endpoint = os.environ.get("S3_ENDPOINT")
        region = os.environ.get("S3_REGION")
        self.default_bucket = os.environ.get("S3_BUCKET")

        # Check for unsigned mode
        use_unsigned = os.environ.get("S3_USE_UNSIGNED", "false").lower() == "true"

        if not endpoint or not self.default_bucket:
             raise RuntimeError(
                "Missing required S3 configuration. S3_ENDPOINT and S3_BUCKET are required."
            )

        if use_unsigned:
            self.client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                region_name=region,
                config=Config(signature_version=UNSIGNED),
            )
        else:
            # Standard auth mode
            access_key = os.environ.get("S3_ACCESS_KEY")
            secret_key = os.environ.get("S3_SECRET_KEY")

            if not access_key or not secret_key:
                 raise RuntimeError(
                    "S3_ACCESS_KEY and S3_SECRET_KEY are required unless S3_USE_UNSIGNED=true."
                )

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

    def download_object(self, key: str, bucket: Optional[str] = None) -> BinaryIO:
        """Download an object from S3-compatible storage."""
        download_bucket = bucket if bucket is not None else self.default_bucket
        try:
            response = self.client.get_object(Bucket=download_bucket, Key=key)

            # Read the response body into a BytesIO object
            data = io.BytesIO(response["Body"].read())

            # Reset to beginning for reading
            data.seek(0)
            return data
        except ClientError as e:
            raise RuntimeError(f"Failed to download object: {e}")

    def get_object_info(self, key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """Get object metadata from S3-compatible storage."""
        info_bucket = bucket if bucket is not None else self.default_bucket
        try:
            response = self.client.head_object(Bucket=info_bucket, Key=key)

            return {
                "bucket": info_bucket,
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
        self,
        key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        method: str = "GET",
        **kwargs,
    ) -> str:
        """Generate a presigned URL for S3-compatible storage object."""
        presigned_bucket = bucket if bucket is not None else self.default_bucket
        try:
            method_upper = method.upper()
            if method_upper == "GET":
                client_method = "get_object"
            elif method_upper == "PUT":
                if "UploadId" in kwargs and "PartNumber" in kwargs:
                    client_method = "upload_part"
                else:
                    client_method = "put_object"
            else:
                raise ValueError(f"Unsupported method: {method}. Use 'GET' or 'PUT'")

            params = {"Bucket": presigned_bucket, "Key": key}
            if "UploadId" in kwargs:
                params["UploadId"] = kwargs["UploadId"]
            if "PartNumber" in kwargs:
                params["PartNumber"] = kwargs["PartNumber"]

            url = self.client.generate_presigned_url(
                ClientMethod=client_method,
                Params=params,
                ExpiresIn=expiration,
            )

            # If a public endpoint is configured, replace the internal endpoint in the URL
            public_endpoint = os.environ.get("S3_PUBLIC_ENDPOINT")
            internal_endpoint = os.environ.get("S3_ENDPOINT")

            if public_endpoint and internal_endpoint and internal_endpoint in url:
                url = url.replace(internal_endpoint, public_endpoint)

            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    def delete_object(self, key: str, bucket: Optional[str] = None) -> bool:
        """Delete an object from S3-compatible storage."""
        delete_bucket = bucket if bucket is not None else self.default_bucket
        try:
            self.client.delete_object(Bucket=delete_bucket, Key=key)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to delete object: {e}")

    def list_objects(
        self,
        prefix: Optional[str] = None,
        bucket: Optional[str] = None,
        max_results: int = 1000,
    ) -> list[Dict[str, Any]]:
        """List objects in an S3-compatible storage bucket."""
        list_bucket = bucket if bucket is not None else self.default_bucket
        try:
            objects = []
            continuation_token = None

            while len(objects) < max_results:
                # Prepare list_objects_v2 parameters
                params = {
                    "Bucket": list_bucket,
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

    def create_multipart_upload(
        self,
        key: str,
        content_type: Optional[str] = None,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Initiate a multipart upload."""
        upload_bucket = bucket if bucket is not None else self.default_bucket
        try:
            params = {
                "Bucket": upload_bucket,
                "Key": key,
                "Metadata": metadata or {},
            }
            if content_type:
                params["ContentType"] = content_type

            response = self.client.create_multipart_upload(**params)
            return response["UploadId"]
        except ClientError as e:
            raise RuntimeError(f"Failed to initiate multipart upload: {e}")

    def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: list[Dict[str, Any]],
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete a multipart upload."""
        upload_bucket = bucket if bucket is not None else self.default_bucket
        try:
            # Sort parts by PartNumber as required by S3
            sorted_parts = sorted(parts, key=lambda p: p["PartNumber"])

            response = self.client.complete_multipart_upload(
                Bucket=upload_bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": sorted_parts},
            )
            return {
                "bucket": response.get("Bucket"),
                "key": response.get("Key"),
                "etag": response.get("ETag", "").strip('"'),
            }
        except ClientError as e:
            raise RuntimeError(f"Failed to complete multipart upload: {e}")

    def abort_multipart_upload(
        self,
        key: str,
        upload_id: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """Abort a multipart upload."""
        upload_bucket = bucket if bucket is not None else self.default_bucket
        try:
            self.client.abort_multipart_upload(
                Bucket=upload_bucket,
                Key=key,
                UploadId=upload_id,
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to abort multipart upload: {e}")
