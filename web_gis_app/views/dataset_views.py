from functools import partial

from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shared.infrastructure import InfraManager

from ..constants import DatasetNodeType
from ..models import DatasetNode
from ..serializers.dataset_serializers import (
    DatasetMultipartCompleteSerializer,
    DatasetMultipartInitSerializer,
    DatasetMultipartSignSerializer,
    DatasetNodeSerializer,
    DatasetNodeTreeSerializer,
    DatasetSerializer,
    DatasetUploadSerializer,
)
from ..services import (
    DatasetCreateService,
    DatasetStorageService,
    MultipartUploadService,
)


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

    def _create_folder(self, request):
        """Create a simple folder node"""
        serializer = DatasetNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, type=DatasetNodeType.FOLDER.value)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _create_dataset(self, request):
        """Create a dataset node with associated file"""
        files = request.FILES.getlist("files")

        if len(files) != 1:
            return Response(
                {"error": "Exactly one file must be uploaded per dataset"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = files[0]

        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dataset_node, dataset = DatasetCreateService.create_dataset_with_file(
                user=request.user,
                validated_data=serializer.validated_data,
                file=file,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = DatasetNodeSerializer(dataset_node).data
        response_data["dataset"] = DatasetSerializer(dataset).data

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _multipart_init(self, request):
        """Initiate a multipart upload"""
        serializer = DatasetMultipartInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = MultipartUploadService.init_multipart_upload(
                user=request.user,
                validated_data=serializer.validated_data,
            )

            return Response(payload)
        except Exception as e:
            return Response(
                {"error": f"Failed to initiate upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _multipart_sign(self, request):
        """Sign a part upload"""
        serializer = DatasetMultipartSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            url = MultipartUploadService.sign_multipart_upload_part(
                validated_data=serializer.validated_data
            )

            return Response({"url": url})
        except Exception as e:
            return Response(
                {"error": f"Failed to sign part: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _multipart_complete(self, request):
        """Complete a multipart upload"""
        serializer = DatasetMultipartCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dataset = MultipartUploadService.complete_multipart_upload(
                validated_data=serializer.validated_data
            )

            return Response(
                {"status": "completed", "dataset": DatasetSerializer(dataset).data}
            )
        except LookupError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to complete upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _multipart_abort(self, request):
        """Abort a multipart upload"""
        upload_id = request.data.get("upload_id")
        key = request.data.get("key")

        if not upload_id or not key:
            return Response(
                {"error": "upload_id (or uploadId) and key are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            MultipartUploadService.abort_multipart_upload(upload_id=upload_id, key=key)

            return Response({"status": "aborted"})
        except Exception as e:
            return Response(
                {"error": f"Failed to abort upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def create(self, request):
        """Create a folder or dataset node"""

        multipart_action = request.query_params.get("multipart")
        if multipart_action:
            if multipart_action == "init":
                return self._multipart_init(request)
            elif multipart_action == "sign":
                return self._multipart_sign(request)
            elif multipart_action == "complete":
                return self._multipart_complete(request)
            elif multipart_action == "abort":
                return self._multipart_abort(request)
            else:
                return Response(
                    {"error": f"Invalid multipart action: {multipart_action}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # For multipart/form-data (file uploads), use request.POST for form fields
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
        storage_paths = list(
            dict.fromkeys(
                DatasetNode.objects.descendants_with_dataset(node)
                .filter(dataset__cloud_storage_path__isnull=False)
                .exclude(dataset__cloud_storage_path="")
                .values_list("dataset__cloud_storage_path", flat=True)
            )
        )

        transaction.on_commit(
            partial(
                DatasetStorageService.delete_dataset_files_from_object_storage,
                storage_paths=storage_paths,
            )
        )

        return super().destroy(request, *args, **kwargs)

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

            return response

        except Exception as e:
            # logger.error(f"Error downloading dataset {dataset.id}: {str(e)}")
            return Response(
                {"error": f"Failed to download file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
