import json

from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shared.infrastructure import InfraManager

from ..constants import DatasetNodeType, DatasetStatus, DatasetType
from ..models import Dataset, DatasetNode, Feature
from ..serializers.dataset_serializers import (
    DatasetMultipartCompleteSerializer,
    DatasetMultipartInitSerializer,
    DatasetMultipartSignSerializer,
    DatasetNodeSerializer,
    DatasetNodeTreeSerializer,
    DatasetSerializer,
    DatasetUploadSerializer,
)
from ..utils import detect_dataset_info


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
        # Handle multipart upload actions via query params
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

        # Build metadata with optional srid and bbox.
        metadata = serializer.validated_data.get("metadata", {})
        if srid := serializer.validated_data.get("srid"):
            metadata["srid"] = srid
        if bbox := serializer.validated_data.get("bbox"):
            metadata["bbox"] = bbox

        # Create the dataset.
        dataset = Dataset.objects.create(
            dataset_node=dataset_node,
            type=dataset_type,
            format=file_format,
            metadata=metadata,
            file_name="",  # Will be set below.
            file_size=0,  # Will be set below.
            cloud_storage_path="",  # Will be set below.
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

        # Save file info and set status to UPLOADED.
        dataset.file_name = file.name
        dataset.file_size = upload_result["size"]
        dataset.cloud_storage_path = cloud_storage_path
        dataset.status = DatasetStatus.UPLOADED
        dataset.save(update_fields=["file_name", "file_size", "cloud_storage_path", "status"])

        # Parse GeoJSON and store features in PostGIS.
        if dataset_type == DatasetType.VECTOR and file_format == "geojson":
            self._parse_and_store_geojson_features(file, dataset)

        # COG generation for raster datasets is now handled by the post_save signal on status=UPLOADED.
        # if dataset_type == DatasetType.RASTER:
        #    generate_cog_task.delay(str(dataset.id))

        # Build response with node and dataset data.
        response_data = DatasetNodeSerializer(dataset_node).data
        response_data["dataset"] = DatasetSerializer(dataset).data

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _multipart_init(self, request):
        """Initiate a multipart upload"""
        serializer = DatasetMultipartInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create DatasetNode and Dataset in "pending" state (or just normal state with incomplete file)
        dataset_node = DatasetNode.objects.create(
            name=serializer.validated_data.get("name"),
            parent=serializer.validated_data.get("parent"),
            type=DatasetNodeType.DATASET.value,
            user=request.user,
        )

        # Determine type/format
        # Note: In multipart init, we don't have the file to check extension/magic bytes easily.
        # We rely on the name or explicit type passed.
        filename = serializer.validated_data.get("name", "unknown")
        try:
            dataset_type, file_format = detect_dataset_info(filename)
            # Override if type is explicitly passed? unique logic might be needed.
            # But here we trust detect_dataset_info or default.
        except ValueError:
            # Fallback or error?
            dataset_type = DatasetType.RASTER # Default? Or error.
            file_format = "tif" # Default

        # Build metadata
        metadata = serializer.validated_data.get("metadata", {})

        dataset = Dataset.objects.create(
            dataset_node=dataset_node,
            type=dataset_type,
            format=file_format,
            metadata=metadata,
            file_name=filename,
            file_size=0,
            cloud_storage_path="", # Will set after generating key
        )

        # Generate key
        file_extension = filename.split(".")[-1] if "." in filename else ""
        key = (
            f"datasets/{dataset.id}/file.{file_extension}"
            if file_extension
            else f"datasets/{dataset.id}/file"
        )
        dataset.cloud_storage_path = key
        # Explicitly set PENDING for multipart init
        dataset.status = DatasetStatus.PENDING
        dataset.save(update_fields=["cloud_storage_path", "status"])

        # Call Infra
        try:
            upload_id = InfraManager.object_storage.create_multipart_upload(
                key=key,
                # contentType? We can guess from extension or metadata
                content_type=metadata.get("content_type"),
                metadata={
                    "dataset_id": str(dataset.id),
                    "original_filename": filename,
                }
            )
            return Response({
                "uploadId": upload_id,
                "key": key,
                "datasetId": dataset.id,
                "nodeId": dataset_node.id
            })
        except Exception as e:
            # Cleanup
            dataset.delete()
            dataset_node.delete()
            return Response(
                {"error": f"Failed to initiate upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _multipart_sign(self, request):
        """Sign a part upload"""
        serializer = DatasetMultipartSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            url = InfraManager.object_storage.generate_presigned_url(
                key=serializer.validated_data["key"],
                method="PUT",
                UploadId=serializer.validated_data["upload_id"],
                PartNumber=serializer.validated_data["part_number"]
            )
            return Response({"url": url})
        except Exception as e:
            return Response(
                {"error": f"Failed to sign part: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _multipart_complete(self, request):
        """Complete a multipart upload"""
        serializer = DatasetMultipartCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        key = serializer.validated_data["key"]

        # Convert parts from snake_case (if sent by frontend mapper) to PascalCase for Boto3
        parts = []
        for part in serializer.validated_data["parts"]:
            parts.append({
                "PartNumber": part.get("PartNumber") or part.get("part_number"),
                "ETag": part.get("ETag") or part.get("e_tag")
            })

        try:
            result = InfraManager.object_storage.complete_multipart_upload(
                key=key,
                upload_id=serializer.validated_data["upload_id"],
                parts=parts
            )

            # Find the dataset associated with this key
            # Standard pattern: datasets/<uuid>/...
            # We can also lookup by cloud_storage_path
            dataset = Dataset.objects.filter(cloud_storage_path=key).first()

            if dataset:
                # Update file info
                # Get head object to get size? Or trust result?
                # Result usually has ETag, doesn't always have size.
                info = InfraManager.object_storage.get_object_info(key=key)
                dataset.file_size = info.get("size", 0)

                # Mark as UPLOADED. This triggers the post_save signal for COG generation.
                dataset.status = DatasetStatus.UPLOADED
                dataset.save(update_fields=["file_size", "status"])

                # Post-processing
                if dataset.type == DatasetType.VECTOR and dataset.format == "geojson":
                    # We need to download and parse?
                    # This might be heavy for synchronous.
                    # Should queue a task.
                    # For now, let's skip automatic parsing for multipart uploads
                    # OR queue a task. existing logic does inline parsing.
                    # Verify task usage. "generate_cog_task" exists.
                    # Maybe create "process_vector_task"?
                    pass

                # RASTER COG generation is now handled by the signal.
                print(f"Dataset {dataset.id} multipart upload completed. Status set to UPLOADED.")

                return Response({
                    "status": "completed",
                    "dataset": DatasetSerializer(dataset).data
                })
            else:
                 return Response(
                    {"error": "Dataset record not found for this key"},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {"error": f"Failed to complete upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _multipart_abort(self, request):
        """Abort a multipart upload"""
        # Frontend mapper might convert to snake_case
        upload_id = request.data.get("upload_id") or request.data.get("uploadId")
        key = request.data.get("key")

        if not upload_id or not key:
             return Response(
                {"error": "upload_id (or uploadId) and key are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            InfraManager.object_storage.abort_multipart_upload(key=key, upload_id=upload_id)

            # Cleanup dataset/node?
            dataset = Dataset.objects.filter(cloud_storage_path=key).first()
            if dataset:
                dataset.status = DatasetStatus.FAILED
                dataset.save(update_fields=["status"])

                node = dataset.dataset_node
                dataset.delete()
                # If node has no other children/datasets? It's 1-to-1.
                node.delete()

            return Response({"status": "aborted"})
        except Exception as e:
            return Response(
                {"error": f"Failed to abort upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_and_store_geojson_features(self, file, dataset: Dataset):
        """
        Parse GeoJSON file and store features in PostGIS.
        """
        try:
            # Reset file pointer to beginning.
            file.seek(0)
            geojson_data = json.load(file)

            features_to_create = []

            if geojson_data.get("type") == "FeatureCollection":
                geojson_features = geojson_data.get("features", [])
            elif geojson_data.get("type") == "Feature":
                geojson_features = [geojson_data]
            else:
                # Assume it's a geometry directly.
                geojson_features = [
                    {"type": "Feature", "geometry": geojson_data, "properties": {}}
                ]

            for feature in geojson_features:
                geometry_json = feature.get("geometry")
                if not geometry_json:
                    continue

                try:
                    geometry = GEOSGeometry(json.dumps(geometry_json), srid=4326)
                    properties = feature.get("properties", {}) or {}

                    features_to_create.append(
                        Feature(
                            dataset=dataset,
                            geometry=geometry,
                            properties=properties,
                        )
                    )
                except Exception as e:
                    print(f"Error creating geometry for feature: {e}")
                    continue

            # Bulk create features.
            if features_to_create:
                Feature.objects.bulk_create(features_to_create, batch_size=1000)
                print(
                    f"Created {len(features_to_create)} features for dataset {dataset.id}"
                )

        except json.JSONDecodeError as e:
            print(f"Error parsing GeoJSON: {e}")
        except Exception as e:
            print(f"Error storing features: {e}")

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
