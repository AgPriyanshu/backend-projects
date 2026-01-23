from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shared.infrastructure import InfraManager

from .models import Dataset, DatasetFile, DatasetNode
from .serializers import (
    DatasetNodeTreeSerializer,
    DatasetSerializer,
    DatasetUploadSerializer,
)


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get all root nodes with their children in a nested tree structure"""
        # Get all root nodes (nodes without a parent)
        root_nodes = DatasetNode.objects.filter(parent__isnull=True).select_related(
            "dataset"
        )

        # Serialize with nested children
        serializer = DatasetNodeTreeSerializer(root_nodes, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        parent_id = request.data.get("parent_id")
        node_type = request.data.get("type")
        files = request.FILES.getlist("files")

        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset_node = DatasetNode.objects.create(
            parent_id=parent_id,
            type=node_type,
            user=request.user
        )

        # Exclude fields that are not part of Dataset model
        dataset_data = serializer.validated_data.copy()
        dataset_data.pop('files', None)  # Remove files field
        dataset_data.pop('type', None)  # Remove node type field (it's for DatasetNode)

        dataset = Dataset.objects.create(dataset_node=dataset_node, **dataset_data)

        uploaded_files = []

        for file in files:
            # Get file extension
            file_extension = file.name.split(".")[-1] if "." in file.name else ""

            # Create DatasetFile record first to get the ID
            dataset_file = DatasetFile.objects.create(
                dataset=dataset,
                cloud_storage_path="",  # Temporary, will update after upload
                file_name=file.name,
                file_size=0,  # Temporary, will update after upload
                mime_type=file.content_type or "application/octet-stream",
                role="main" if len(files) == 1 else "additional",
            )

            # Generate cloud storage path using DatasetFile ID
            cloud_storage_path = (
                f"datasets/{dataset.id}/{dataset_file.id}.{file_extension}"
                if file_extension
                else f"datasets/{dataset.id}/{dataset_file.id}"
            )

            # Upload to object storage
            upload_result = InfraManager.object_storage.upload_object(
                file=file,
                key=cloud_storage_path,
                metadata={
                    "dataset_id": str(dataset.id),
                    "dataset_file_id": str(dataset_file.id),
                    "original_filename": file.name,
                    "content_type": file.content_type or "application/octet-stream",
                },
            )

            # Update DatasetFile with actual cloud path and size
            dataset_file.cloud_storage_path = cloud_storage_path
            dataset_file.file_size = upload_result["size"]
            dataset_file.save(update_fields=["cloud_storage_path", "file_size"])

            uploaded_files.append(dataset_file)

        response_data = DatasetSerializer(dataset).data
        response_data["files"] = [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_size": f.file_size,
                "cloud_storage_path": f.cloud_storage_path,
            }
            for f in uploaded_files
        ]

        return Response(response_data, status=status.HTTP_201_CREATED)
