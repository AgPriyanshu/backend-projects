from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Layer, Feature, FeatureAttribute
from .serializers import (
    LayerSerializer,
    LayerListSerializer,
    FeatureSerializer,
    ShapefileUploadSerializer,
)
from .shapefile_processor import process_shapefile_upload, get_shapefile_preview
from .utils import AttributeManager


class LayerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing layers
    Provides CRUD operations for layers plus custom actions
    """

    queryset = Layer.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return LayerListSerializer
        return LayerSerializer

    @action(
        detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser]
    )
    def upload(self, request):
        """
        Upload and process shapefile zip files
        POST /api/layers/upload/
        """
        serializer = ShapefileUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get validated data
            zip_file = serializer.validated_data["file"]
            layer_name = serializer.validated_data["layer_name"]
            description = serializer.validated_data.get("description", "")

            # Process the shapefile
            with transaction.atomic():
                layer, processing_stats = process_shapefile_upload(
                    zip_file, layer_name, description
                )

            # Serialize the created layer
            layer_serializer = LayerSerializer(layer)

            return Response(
                {
                    "success": True,
                    "message": f'Successfully imported {processing_stats["features_created"]} features',
                    "layer": layer_serializer.data,
                    "processing_stats": processing_stats,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response(
                {"error": "Invalid shapefile", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Processing failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser]
    )
    def preview(self, request):
        """
        Preview shapefile information without importing
        POST /api/layers/preview/
        """
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        zip_file = request.FILES["file"]

        if not zip_file.name.endswith(".zip"):
            return Response(
                {"error": "File must be a ZIP archive containing shapefile components"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            preview_info = get_shapefile_preview(zip_file)
            return Response({"success": True, "shapefile_info": preview_info})

        except ValueError as e:
            return Response(
                {"error": "Invalid shapefile", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Preview failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def features(self, request, pk=None):
        """
        List features for a specific layer
        GET /api/layers/{id}/features/
        """
        layer = self.get_object()
        features = Feature.objects.filter(layer=layer).prefetch_related("attributes")
        serializer = FeatureSerializer(features, many=True)

        return Response(
            {
                "success": True,
                "layer_id": layer.id,
                "layer_name": layer.name,
                "feature_count": len(features),
                "features": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="attributes/summary")
    def attributes_summary(self, request, pk=None):
        """
        Get attribute summary for a layer
        GET /api/layers/{id}/attributes/summary/
        """
        layer = self.get_object()

        try:
            summary = AttributeManager.get_layer_attribute_summary(layer)
            return Response(
                {
                    "success": True,
                    "layer_id": layer.id,
                    "layer_name": layer.name,
                    "attribute_summary": summary,
                }
            )
        except Exception as e:
            return Response(
                {"error": "Failed to generate summary", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["get"],
        url_path="attributes/(?P<attribute_key>[^/.]+)/stats",
    )
    def attribute_stats(self, request, pk=None, attribute_key=None):
        """
        Get statistics for a specific attribute in a layer
        GET /api/layers/{id}/attributes/{attribute_key}/stats/
        """
        layer = self.get_object()

        try:
            stats = AttributeManager.get_attribute_statistics(layer, attribute_key)

            if not stats:
                return Response(
                    {"error": f'Attribute "{attribute_key}" not found in layer'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "success": True,
                    "layer_id": layer.id,
                    "attribute_key": attribute_key,
                    "statistics": stats,
                }
            )
        except Exception as e:
            return Response(
                {"error": "Failed to generate statistics", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="features/filter")
    def filter_features(self, request, pk=None):
        """
        Filter features by attribute values
        POST /api/layers/{id}/features/filter/

        Request body example:
        {
            "filters": {
                "population": {"min": 1000, "max": 50000},
                "type": "city"
            }
        }
        """
        layer = self.get_object()

        filters = request.data.get("filters", {})
        if not filters:
            return Response(
                {"error": "No filters provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            features = AttributeManager.get_features_by_attribute_filter(layer, filters)
            serializer = FeatureSerializer(features, many=True)

            return Response(
                {
                    "success": True,
                    "layer_id": layer.id,
                    "filters_applied": filters,
                    "feature_count": len(features),
                    "features": serializer.data,
                }
            )
        except Exception as e:
            return Response(
                {"error": "Filter failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """
        Export layer attributes as table data
        GET /api/layers/{id}/export/
        """
        layer = self.get_object()

        try:
            table_data = AttributeManager.export_attributes_table(layer)

            return Response(
                {
                    "success": True,
                    "layer_id": layer.id,
                    "layer_name": layer.name,
                    "feature_count": len(table_data),
                    "data": table_data,
                }
            )
        except Exception as e:
            return Response(
                {"error": "Export failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FeatureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reading features
    Provides read-only access to features
    """

    serializer_class = FeatureSerializer

    def get_queryset(self):
        return Feature.objects.prefetch_related("attributes").order_by("-created_at")

    @action(detail=True, methods=["get"])
    def attributes(self, request, pk=None):
        """
        Get all attributes for a specific feature
        GET /api/features/{id}/attributes/
        """
        feature = self.get_object()
        attributes = feature.attributes.all()

        attribute_data = {}
        for attr in attributes:
            attribute_data[attr.key] = {
                "value": attr.value,
                "data_type": attr.data_type,
                "typed_value": attr.get_typed_value(),
            }

        return Response(
            {
                "success": True,
                "feature_id": feature.id,
                "layer_name": feature.layer.name,
                "attributes": attribute_data,
            }
        )


class FeatureAttributeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reading feature attributes
    Provides read-only access to feature attributes
    """

    queryset = FeatureAttribute.objects.all().order_by("-created_at")
    serializer_class = None  # We'll use custom responses

    def list(self, request):
        """List all feature attributes with optional filtering"""
        queryset = self.get_queryset()

        # Filter by layer if provided
        layer_id = request.query_params.get("layer_id")
        if layer_id:
            queryset = queryset.filter(feature__layer_id=layer_id)

        # Filter by key if provided
        key = request.query_params.get("key")
        if key:
            queryset = queryset.filter(key=key)

        # Filter by data type if provided
        data_type = request.query_params.get("data_type")
        if data_type:
            queryset = queryset.filter(data_type=data_type)

        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            attributes_data = []
            for attr in page:
                attributes_data.append(
                    {
                        "id": attr.id,
                        "feature_id": attr.feature.id,
                        "layer_name": attr.feature.layer.name,
                        "key": attr.key,
                        "value": attr.value,
                        "data_type": attr.data_type,
                        "typed_value": attr.get_typed_value(),
                        "created_at": attr.created_at,
                    }
                )
            return self.get_paginated_response(attributes_data)

        return Response(
            {
                "success": True,
                "count": queryset.count(),
                "attributes": [
                    {
                        "id": attr.id,
                        "feature_id": attr.feature.id,
                        "layer_name": attr.feature.layer.name,
                        "key": attr.key,
                        "value": attr.value,
                        "data_type": attr.data_type,
                        "typed_value": attr.get_typed_value(),
                        "created_at": attr.created_at,
                    }
                    for attr in queryset[:100]  # Limit to 100 items
                ],
            }
        )
