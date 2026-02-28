import logging

from shared.infrastructure import InfraManager

from .constants import DatasetNodeType, DatasetStatus, DatasetType, FileFormat
from .models import Dataset, DatasetNode
from .utils import detect_dataset_format

logger = logging.getLogger(__name__)


class DatasetStorageService:
    @staticmethod
    def build_dataset_storage_key(*, dataset_id, filename):
        file_extension = filename.split(".")[-1] if "." in filename else ""

        if file_extension:
            return f"datasets/{dataset_id}/file.{file_extension}"

        return f"datasets/{dataset_id}/file"

    @staticmethod
    def delete_dataset_files_from_object_storage(storage_paths):
        for storage_path in storage_paths:
            if not storage_path:
                continue

            try:
                InfraManager.object_storage.delete_object(key=storage_path)
            except Exception:
                logger.exception(
                    "Error deleting file from object storage: %s.", storage_path
                )


class DatasetCreateService:
    @staticmethod
    def create_dataset_with_file(*, user, validated_data, file):
        file_format = detect_dataset_format(file.name)
        dataset_type = validated_data.get("dataset_type") or MultipartUploadService._infer_dataset_type(
            file_format=file_format
        )

        dataset_node = DatasetNode.objects.create(
            name=validated_data.get("name"),
            parent=validated_data.get("parent"),
            type=DatasetNodeType.DATASET.value,
            user=user,
        )

        metadata = dict(validated_data.get("metadata", {}))

        if srid := validated_data.get("srid"):
            metadata["srid"] = srid

        if bbox := validated_data.get("bbox"):
            metadata["bbox"] = bbox

        dataset = Dataset.objects.create(
            dataset_node=dataset_node,
            type=dataset_type,
            format=file_format,
            metadata=metadata,
            file_name="",
            file_size=0,
            cloud_storage_path="",
            status=DatasetStatus.PENDING,
        )

        cloud_storage_path = DatasetStorageService.build_dataset_storage_key(
            dataset_id=dataset.id,
            filename=file.name,
        )

        upload_result = InfraManager.object_storage.upload_object(
            file=file,
            key=cloud_storage_path,
            metadata={
                "dataset_id": str(dataset.id),
                "original_filename": file.name,
                "content_type": file.content_type or "application/octet-stream",
            },
        )

        dataset.file_name = file.name
        dataset.file_size = upload_result["size"]
        dataset.cloud_storage_path = cloud_storage_path
        dataset.status = DatasetStatus.UPLOADED
        dataset.save(
            update_fields=["file_name", "file_size", "cloud_storage_path", "status"]
        )

        return dataset_node, dataset


class MultipartUploadService:
    @staticmethod
    def init_multipart_upload(*, user, validated_data):
        filename = validated_data.get("name", "unknown")
        explicit_dataset_type = validated_data.get("dataset_type")
        metadata = dict(validated_data.get("metadata", {}))
        file_format = MultipartUploadService._get_file_format_for_multipart_init(
            filename=filename,
            explicit_dataset_type=explicit_dataset_type,
        )
        dataset_type = (
            explicit_dataset_type
            or MultipartUploadService._infer_dataset_type(file_format=file_format)
        )

        dataset_node = DatasetNode.objects.create(
            name=validated_data.get("name"),
            parent=validated_data.get("parent"),
            type=DatasetNodeType.DATASET.value,
            user=user,
        )

        dataset = Dataset.objects.create(
            dataset_node=dataset_node,
            type=dataset_type,
            format=file_format,
            metadata=metadata,
            file_name=filename,
            file_size=0,
            cloud_storage_path="",
        )

        key = DatasetStorageService.build_dataset_storage_key(
            dataset_id=dataset.id,
            filename=filename,
        )
        dataset.cloud_storage_path = key
        dataset.status = DatasetStatus.PENDING
        dataset.save(update_fields=["cloud_storage_path", "status"])

        try:
            upload_id = InfraManager.object_storage.create_multipart_upload(
                key=key,
                content_type=metadata.get("content_type"),
                metadata={
                    "dataset_id": str(dataset.id),
                    "original_filename": filename,
                },
            )
        except Exception:
            dataset.delete()
            dataset_node.delete()
            raise

        return {
            "uploadId": upload_id,
            "key": key,
            "datasetId": dataset.id,
            "nodeId": dataset_node.id,
        }

    @staticmethod
    def sign_multipart_upload_part(*, validated_data):
        kwargs = {
            "UploadId": validated_data["upload_id"],
            "PartNumber": validated_data["part_number"],
        }
        return InfraManager.object_storage.generate_presigned_url(
            key=validated_data["key"],
            method="PUT",
            **kwargs,
        )

    @staticmethod
    def complete_multipart_upload(*, validated_data):
        key = validated_data["key"]
        parts = []

        for part in validated_data["parts"]:
            parts.append(
                {
                    "PartNumber": part.get("PartNumber") or part.get("part_number"),
                    "ETag": part.get("ETag") or part.get("e_tag"),
                }
            )

        InfraManager.object_storage.complete_multipart_upload(
            key=key,
            upload_id=validated_data["upload_id"],
            parts=parts,
        )

        dataset = Dataset.objects.filter(cloud_storage_path=key).first()

        if dataset is None:
            raise LookupError("Dataset record not found for this key")

        info = InfraManager.object_storage.get_object_info(key=key)
        dataset.file_size = info.get("size", 0)
        dataset.status = DatasetStatus.UPLOADED
        dataset.save(update_fields=["file_size", "status"])

        return dataset

    @staticmethod
    def abort_multipart_upload(*, upload_id, key):
        InfraManager.object_storage.abort_multipart_upload(
            key=key,
            upload_id=upload_id,
        )

        dataset = Dataset.objects.filter(cloud_storage_path=key).first()

        if dataset:
            dataset.status = DatasetStatus.FAILED
            dataset.save(update_fields=["status"])
            node = dataset.dataset_node
            dataset.delete()
            node.delete()

    @staticmethod
    def _get_file_format_for_multipart_init(*, filename, explicit_dataset_type):
        try:
            return detect_dataset_format(filename)
        except ValueError:
            if explicit_dataset_type:
                return filename.split(".")[-1] if "." in filename else "bin"

            return FileFormat.GEOTIFF

    @staticmethod
    def _infer_dataset_type(*, file_format):
        if file_format in {
            FileFormat.SHAPEFILE,
            FileFormat.KML,
            FileFormat.GEOPACKAGE,
        }:
            return DatasetType.VECTOR

        if file_format in {
            FileFormat.GEOTIFF,
            FileFormat.COG,
            FileFormat.PNG,
            FileFormat.JPEG,
        }:
            return DatasetType.RASTER

        return DatasetType.TEXT
