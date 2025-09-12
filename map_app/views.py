from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Layer, Feature, FeatureAttribute
from .serializers import (
    LayerSerializer,
    LayerListSerializer,
    LayerGeoJSONSerializer,
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
    permission_classes = [AllowAny]  # Allow access without authentication

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

            # Check if processing was actually successful
            features_created = processing_stats["features_created"]
            errors = processing_stats.get("errors", [])
            
            # If no features were created and there are errors, treat as failure
            if features_created == 0 and errors:
                # Delete the layer since no features were created
                layer.delete()
                
                # Return detailed error information
                error_summary = errors[:5]  # Show first 5 errors
                if len(errors) > 5:
                    error_summary.append(f"... and {len(errors) - 5} more errors")
                    
                return Response(
                    {
                        "success": False,
                        "error": "Shapefile processing failed",
                        "details": f"No features could be imported. {len(errors)} errors occurred during processing.",
                        "errors": error_summary,
                        "processing_stats": processing_stats,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # If some features were created but there were also errors, show warning
            elif features_created > 0 and errors:
                layer_serializer = LayerSerializer(layer)
                return Response(
                    {
                        "success": True,
                        "warning": f"Partial import: {features_created} features imported, but {len(errors)} errors occurred",
                        "message": f'Successfully imported {features_created} features with {len(errors)} errors',
                        "layer": layer_serializer.data,
                        "processing_stats": processing_stats,
                    },
                    status=status.HTTP_201_CREATED,
                )
            
            # Complete success - no errors
            else:
                layer_serializer = LayerSerializer(layer)
                return Response(
                    {
                        "success": True,
                        "message": f'Successfully imported {features_created} features',
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
            return Response({"success": True, "preview": preview_info})

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

    @action(detail=True, methods=["get"])
    def geojson(self, request, pk=None):
        """
        Get layer data as GeoJSON for map visualization
        GET /api/layers/{id}/geojson/
        """
        layer = self.get_object()
        
        try:
            serializer = LayerGeoJSONSerializer(layer)
            # Return the GeoJSON directly as expected by frontend
            return Response(serializer.data['geojson'])
        except Exception as e:
            return Response(
                {"error": "Failed to generate GeoJSON", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="analytics/population")
    def analyze_population(self, request, pk=None):
        """
        Analyze population data in the layer
        POST /api/layers/{id}/analytics/population/
        
        Request body:
        {
            "population_field": "pop_est",
            "operation": "greater_than",  // "greater_than", "less_than", "between", "top_n"
            "threshold": 10000000,
            "threshold_max": 50000000,  // for "between" operation
            "n": 10  // for "top_n" operation
        }
        """
        layer = self.get_object()
        
        population_field = request.data.get("population_field")
        operation = request.data.get("operation", "greater_than")
        threshold = request.data.get("threshold")
        threshold_max = request.data.get("threshold_max")
        n = request.data.get("n")
        
        if not population_field:
            return Response(
                {"error": "population_field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get statistics for the population field
            stats = AttributeManager.get_attribute_statistics(layer, population_field)
            if not stats:
                return Response(
                    {"error": f"Field '{population_field}' not found in layer"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Build filters based on operation
            filters = []
            
            if operation == "greater_than" and threshold is not None:
                filters = [{"field": population_field, "operator": "gt", "value": threshold}]
            elif operation == "less_than" and threshold is not None:
                filters = [{"field": population_field, "operator": "lt", "value": threshold}]
            elif operation == "between" and threshold is not None and threshold_max is not None:
                filters = [
                    {"field": population_field, "operator": "gte", "value": threshold},
                    {"field": population_field, "operator": "lte", "value": threshold_max}
                ]
            elif operation == "top_n" and n is not None:
                # Get all features and sort by population
                all_features = Feature.objects.filter(layer=layer).prefetch_related("attributes")
                feature_populations = []
                
                for feature in all_features:
                    pop_attr = feature.attributes.filter(key=population_field).first()
                    if pop_attr and pop_attr.numeric_value is not None:
                        feature_populations.append((feature, pop_attr.numeric_value))
                
                # Sort by population descending and take top n
                feature_populations.sort(key=lambda x: x[1], reverse=True)
                top_features = [fp[0] for fp in feature_populations[:n]]
                
                result = {
                    "success": True,
                    "layer_id": layer.id,
                    "operation": operation,
                    "population_field": population_field,
                    "statistics": stats,
                    "matching_features": len(top_features),
                    "features": FeatureSerializer(top_features, many=True).data
                }
                
                return Response(result)
            
            if not filters:
                return Response(
                    {"error": "Invalid operation parameters"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply filters
            filtered_features = AttributeManager.get_features_by_attribute_filter(layer, {
                population_field: filters[0] if len(filters) == 1 else filters
            })
            
            result = {
                "success": True,
                "layer_id": layer.id,
                "operation": operation,
                "population_field": population_field,
                "statistics": stats,
                "matching_features": len(filtered_features),
                "features": FeatureSerializer(filtered_features, many=True).data
            }
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {"error": "Population analysis failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="analytics/spatial")
    def spatial_analysis(self, request, pk=None):
        """
        Perform spatial analysis operations
        POST /api/layers/{id}/analytics/spatial/
        
        Request body:
        {
            "operation": "buffer",  // "buffer", "area", "centroid", "within_distance"
            "parameters": {
                "distance": 1000,  // for buffer and within_distance operations
                "units": "meters",
                "target_layer_id": 2  // for intersection operations
            }
        }
        """
        layer = self.get_object()
        
        operation = request.data.get("operation")
        parameters = request.data.get("parameters", {})
        
        if not operation:
            return Response(
                {"error": "operation is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D
            from django.contrib.gis.db.models import Area, Distance
            
            features = Feature.objects.filter(layer=layer).select_related("layer")
            results = []
            
            if operation == "area":
                # Calculate area for each feature
                for feature in features:
                    if hasattr(feature.geometry, 'area'):
                        area_m2 = feature.geometry.area
                        area_km2 = area_m2 / 1000000
                        results.append({
                            "feature_id": feature.id,
                            "area_m2": area_m2,
                            "area_km2": area_km2
                        })
                
                return Response({
                    "success": True,
                    "layer_id": layer.id,
                    "operation": operation,
                    "results": results
                })
            
            elif operation == "centroid":
                # Calculate centroid for each feature
                for feature in features:
                    centroid = feature.geometry.centroid
                    results.append({
                        "feature_id": feature.id,
                        "centroid": {
                            "longitude": centroid.x,
                            "latitude": centroid.y
                        }
                    })
                
                return Response({
                    "success": True,
                    "layer_id": layer.id,
                    "operation": operation,
                    "results": results
                })
            
            elif operation == "buffer":
                distance = parameters.get("distance", 1000)
                # Create buffer around each feature
                for feature in features:
                    buffered_geom = feature.geometry.buffer(distance)
                    results.append({
                        "feature_id": feature.id,
                        "buffer_distance": distance,
                        "buffer_area": buffered_geom.area if hasattr(buffered_geom, 'area') else None
                    })
                
                return Response({
                    "success": True,
                    "layer_id": layer.id,
                    "operation": operation,
                    "results": results
                })
            
            else:
                return Response(
                    {"error": f"Spatial operation '{operation}' not implemented"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {"error": "Spatial analysis failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="analytics/advanced-filter")
    def advanced_filter(self, request, pk=None):
        """
        Advanced filtering with multiple conditions and operations
        POST /api/layers/{id}/analytics/advanced-filter/
        
        Request body:
        {
            "filters": [
                {"field": "population", "operator": "gt", "value": 1000000},
                {"field": "gdp_per_capita", "operator": "lt", "value": 50000},
                {"field": "continent", "operator": "in", "value": ["Asia", "Europe"]}
            ],
            "logic": "and",  // "and" or "or"
            "limit": 100,
            "include_geojson": true
        }
        """
        layer = self.get_object()
        
        filters = request.data.get("filters", [])
        logic = request.data.get("logic", "and")
        limit = request.data.get("limit", 100)
        include_geojson = request.data.get("include_geojson", False)
        
        if not filters:
            return Response(
                {"error": "filters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Build complex query
            from django.db.models import Q
            
            query = Q()
            for filter_item in filters:
                field = filter_item.get("field")
                operator = filter_item.get("operator")
                value = filter_item.get("value")
                
                if not all([field, operator, value is not None]):
                    continue
                
                # Build Q object based on operator
                if operator == "eq":
                    condition = Q(attributes__key=field, attributes__value=str(value))
                elif operator == "gt":
                    condition = Q(attributes__key=field, attributes__numeric_value__gt=float(value))
                elif operator == "lt":
                    condition = Q(attributes__key=field, attributes__numeric_value__lt=float(value))
                elif operator == "gte":
                    condition = Q(attributes__key=field, attributes__numeric_value__gte=float(value))
                elif operator == "lte":
                    condition = Q(attributes__key=field, attributes__numeric_value__lte=float(value))
                elif operator == "contains":
                    condition = Q(attributes__key=field, attributes__value__icontains=str(value))
                elif operator == "in":
                    if isinstance(value, list):
                        condition = Q(attributes__key=field, attributes__value__in=[str(v) for v in value])
                    else:
                        condition = Q(attributes__key=field, attributes__value=str(value))
                else:
                    continue
                
                # Apply logic
                if logic == "and":
                    query = query & condition
                else:  # or
                    query = query | condition
            
            # Execute query
            features = Feature.objects.filter(layer=layer).filter(query).distinct()[:limit]
            
            result = {
                "success": True,
                "layer_id": layer.id,
                "filters_applied": filters,
                "logic": logic,
                "matching_features": len(features),
                "features": FeatureSerializer(features, many=True).data
            }
            
            if include_geojson:
                # Convert to GeoJSON
                from django.contrib.gis.serializers import geojson
                geojson_data = geojson.Serializer().serialize(features, geometry_field='geometry')
                result["geojson"] = geojson_data
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {"error": "Advanced filtering failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="analytics/visualization")
    def create_visualization(self, request, pk=None):
        """
        Create visualization data for the layer
        POST /api/layers/{id}/analytics/visualization/
        
        Request body:
        {
            "style_field": "population",
            "style_type": "choropleth",  // "choropleth", "categorical", "graduated", "simple"
            "color_scheme": "blues",
            "breaks": 5,
            "feature_ids": [1, 2, 3]  // optional, specific features to highlight
        }
        """
        layer = self.get_object()
        
        style_field = request.data.get("style_field")
        style_type = request.data.get("style_type", "simple")
        color_scheme = request.data.get("color_scheme", "blues")
        breaks = request.data.get("breaks", 5)
        feature_ids = request.data.get("feature_ids")
        
        try:
            # Get layer as GeoJSON
            serializer = LayerGeoJSONSerializer(layer)
            geojson_data = serializer.data
            
            # Generate visualization config
            visualization_config = {
                "type": "map_visualization",
                "layer_id": layer.id,
                "layer_name": layer.name,
                "style_type": style_type,
                "color_scheme": color_scheme,
                "geojson": geojson_data,
                "feature_count": len(geojson_data.get("features", []))
            }
            
            if style_field:
                # Get statistics for the style field
                stats = AttributeManager.get_attribute_statistics(layer, style_field)
                if stats:
                    visualization_config.update({
                        "style_field": style_field,
                        "field_stats": stats,
                        "breaks": breaks
                    })
                    
                    # Generate break values for choropleth
                    if style_type == "choropleth" and stats.get("min") is not None and stats.get("max") is not None:
                        min_val = stats["min"]
                        max_val = stats["max"]
                        step = (max_val - min_val) / breaks
                        break_values = [min_val + (i * step) for i in range(breaks + 1)]
                        visualization_config["break_values"] = break_values
            
            if feature_ids:
                visualization_config["highlighted_features"] = feature_ids
            
            return Response({
                "success": True,
                "visualization": visualization_config
            })
            
        except Exception as e:
            return Response(
                {"error": "Visualization creation failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="analytics/summary")
    def layer_summary(self, request, pk=None):
        """
        Get comprehensive layer summary for AI analysis
        GET /api/layers/{id}/analytics/summary/
        """
        layer = self.get_object()
        
        try:
            # Get basic layer info
            summary = {
                "layer_id": layer.id,
                "layer_name": layer.name,
                "description": layer.description,
                "created_at": layer.created_at,
                "feature_count": layer.features.count()
            }
            
            # Get attribute summary
            attr_summary = AttributeManager.get_layer_attribute_summary(layer)
            summary["attributes"] = attr_summary
            
            # Get spatial extent
            features = layer.features.all()
            if features:
                from django.contrib.gis.geos import MultiPoint
                
                # Get all centroids
                centroids = [f.geometry.centroid for f in features if f.geometry]
                if centroids:
                    multi_point = MultiPoint(centroids)
                    extent = multi_point.extent  # (xmin, ymin, xmax, ymax)
                    summary["spatial_extent"] = {
                        "xmin": extent[0],
                        "ymin": extent[1], 
                        "xmax": extent[2],
                        "ymax": extent[3]
                    }
            
            # Get sample features
            sample_features = features[:3]
            summary["sample_features"] = FeatureSerializer(sample_features, many=True).data
            
            return Response({
                "success": True,
                "summary": summary
            })
            
        except Exception as e:
            return Response(
                {"error": "Summary generation failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FeatureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reading features
    Provides read-only access to features
    """

    serializer_class = FeatureSerializer
    permission_classes = [AllowAny]  # Allow access without authentication

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
    permission_classes = [AllowAny]  # Allow access without authentication

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
