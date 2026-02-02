from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shared.infrastructure import InfraManager

from .constants import DatasetNodeType
from .models import Dataset, DatasetNode
from .serializers import (
    DatasetNodeSerializer,
    DatasetNodeTreeSerializer,
    DatasetSerializer,
    DatasetUploadSerializer,
)
from .utils import detect_dataset_info


class DatasetNodeViewSet(ModelViewSet):
    """
    ViewSet for managing the dataset tree structure.
    Handles both folders and datasets (nodes with associated data files).
    """

    queryset = DatasetNode.objects.all()
    serializer_class = DatasetNodeSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use tree serializer for list view"""
        if self.action == "list":
            return DatasetNodeTreeSerializer
        return DatasetNodeSerializer

    def list(self, request):
        """Get all root nodes with their children in a nested tree structure"""
        root_nodes = DatasetNode.objects.filter(parent__isnull=True).select_related(
            "dataset"
        )
        serializer = self.get_serializer(root_nodes, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        """Create a folder or dataset node"""
        # For multipart/form-data (file uploads), use request.POST for form fields
        # For JSON requests, use request.data
        data_source = request.POST if request.FILES else request.data
        node_type = data_source.get("type")

        if node_type == DatasetNodeType.FOLDER.value:
            return self._create_folder(request)
        elif node_type == DatasetNodeType.DATASET.value:
            return self._create_dataset(request)
        else:
            return Response(
                {"error": "Invalid type. Must be 'folder' or 'dataset'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Delete node and cleanup associated files. If folder, deletes full hierarchy."""
        node = self.get_object()
        # Use closure table to efficiently get all descendants (including self)
        # This gets all nodes where the current node is an ancestor
        descendant_ids = node.ancestor_closures.values_list("descendant_id", flat=True)
        nodes_to_process = DatasetNode.objects.filter(
            id__in=descendant_ids
        ).select_related("dataset")

        # Clean up files from object storage for all nodes with datasets
        for node_to_delete in nodes_to_process:
            if hasattr(node_to_delete, "dataset") and node_to_delete.dataset:
                dataset = node_to_delete.dataset

                # Delete the file
                if dataset.cloud_storage_path:
                    try:
                        InfraManager.object_storage.delete_object(
                            key=dataset.cloud_storage_path
                        )
                    except Exception as e:
                        print(f"Error deleting file {dataset.cloud_storage_path}: {e}")

        # Delete the node (will cascade to all children, datasets, and dataset files in DB)
        return super().destroy(request, *args, **kwargs)

    def _create_folder(self, request):
        """Create a simple folder node"""
        serializer = DatasetNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, type=DatasetNodeType.FOLDER.value)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _create_dataset(self, request):
        """Create a dataset node with associated file"""
        files = request.FILES.getlist("files")

        # Ensure only one file is uploaded
        if len(files) != 1:
            return Response(
                {"error": "Exactly one file must be uploaded per dataset"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = files[0]

        # Auto-detect dataset type and format from file extension
        try:
            dataset_type, file_format = detect_dataset_info(file.name)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the upload data
        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset_node = DatasetNode.objects.create(
            name=serializer.validated_data.get("name"),
            parent=serializer.validated_data.get("parent"),
            type=DatasetNodeType.DATASET.value,
            user=request.user,
        )

        # Create the dataset
        dataset = Dataset.objects.create(
            dataset_node=dataset_node,
            type=dataset_type,
            format=file_format,
            srid=serializer.validated_data.get("srid"),
            bbox=serializer.validated_data.get("bbox"),
            metadata=serializer.validated_data.get("metadata", {}),
            file_name="",  # Will be set below
            file_size=0,  # Will be set below
            cloud_storage_path="",  # Will be set below
        )

        # Upload file
        file_extension = file.name.split(".")[-1] if "." in file.name else ""
        cloud_storage_path = (
            f"datasets/{dataset.id}/file.{file_extension}"
            if file_extension
            else f"datasets/{dataset.id}/file"
        )

        # Upload to object storage
        upload_result = InfraManager.object_storage.upload_object(
            file=file,
            key=cloud_storage_path,
            metadata={
                "dataset_id": str(dataset.id),
                "original_filename": file.name,
                "content_type": file.content_type or "application/octet-stream",
            },
        )

        # Save file info
        dataset.file_name = file.name
        dataset.file_size = upload_result["size"]
        dataset.cloud_storage_path = cloud_storage_path
        dataset.save(update_fields=["file_name", "file_size", "cloud_storage_path"])

        # Build response with node and dataset data
        response_data = DatasetNodeSerializer(dataset_node).data
        response_data["dataset"] = DatasetSerializer(dataset).data

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(methods=["GET"], detail=True, url_path="download", url_name="download")
    def download(self, request, pk):
        """Download the dataset file from object storage"""
        dataset_node = self.get_object()

        # Check if this node has an associated dataset
        if not hasattr(dataset_node, "dataset") or not dataset_node.dataset:
            return Response(
                {"error": "This node does not have an associated dataset file"},
                status=status.HTTP_404_NOT_FOUND,
            )

        dataset = dataset_node.dataset

        # Check if the dataset has a cloud storage path
        if not dataset.cloud_storage_path:
            return Response(
                {"error": "Dataset file not found in storage"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Download the file from object storage
            # The K8sObjectStorage uses a default bucket, so we need to pass it
            file_data = InfraManager.object_storage.download_object(
                key=dataset.cloud_storage_path
            )

            # Create a FileResponse with the downloaded file
            response = FileResponse(
                file_data, as_attachment=True, filename=dataset.file_name
            )

            # Set content type if available
            if dataset.metadata and dataset.metadata.get("content_type"):
                response["Content-Type"] = dataset.metadata["content_type"]

            # logger.debug()

            return response

        except Exception as e:
            # logger.error(f"Error downloading dataset {dataset.id}: {str(e)}")
            return Response(
                {"error": f"Failed to download file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
