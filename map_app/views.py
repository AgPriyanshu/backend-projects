import os
import json
import time
from typing import Dict, Any
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import numpy as np
from PIL import Image
import tempfile
import logging

from .models import GeospatialImage, ObjectDetection, DetectedObject
from .serializers import (
    GeospatialImageSerializer,
    GeospatialImageDetailSerializer,
    ObjectDetectionSerializer
)

logger = logging.getLogger(__name__)


class GeospatialImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing geospatial images and object detection"""
    serializer_class = GeospatialImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return GeospatialImage.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GeospatialImageDetailSerializer
        return GeospatialImageSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def detect_objects(self, request, pk=None):
        """
        Perform object detection on the geospatial image using SAM-Geo
        """
        try:
            geospatial_image = self.get_object()
            
            # Update status to processing
            geospatial_image.processing_status = 'processing'
            geospatial_image.save()

            # Get parameters from request
            confidence_threshold = float(request.data.get('confidence_threshold', 0.5))
            model_type = request.data.get('model_type', 'vit_h')

            # Process the image with SAM-Geo
            start_time = time.time()
            detection_results = self._process_with_samgeo(
                geospatial_image.original_image.path,
                confidence_threshold,
                model_type
            )
            processing_time = time.time() - start_time

            # Create ObjectDetection record
            object_detection = ObjectDetection.objects.create(
                geospatial_image=geospatial_image,
                detection_data=detection_results,
                confidence_threshold=confidence_threshold,
                model_version=model_type,
                processing_time=processing_time
            )

            # Create individual DetectedObject records
            for i, feature in enumerate(detection_results.get('features', [])):
                DetectedObject.objects.create(
                    detection=object_detection,
                    geometry=feature['geometry'],
                    properties=feature['properties'],
                    confidence_score=feature['properties'].get('confidence', 0.0),
                    area=feature['properties'].get('area', None)
                )

            # Update status to completed
            geospatial_image.processing_status = 'completed'
            geospatial_image.save()

            serializer = ObjectDetectionSerializer(object_detection)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing image {pk}: {str(e)}")
            geospatial_image.processing_status = 'failed'
            geospatial_image.save()
            return Response(
                {'error': f'Failed to process image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_with_samgeo(self, image_path: str, confidence_threshold: float, model_type: str) -> Dict[str, Any]:
        """
        Process image with SAM-Geo for object detection
        """
        try:
            # Import SAM-Geo (only when needed to avoid startup issues if not installed)
            from samgeo import SamGeo
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Initialize SAM-Geo
                sam = SamGeo(
                    model_type=model_type,
                    automatic=True,
                    sam_kwargs={
                        "points_per_side": 32,
                        "pred_iou_thresh": 0.86,
                        "stability_score_thresh": 0.92,
                        "crop_n_layers": 1,
                        "crop_n_points_downscale_factor": 2,
                        "min_mask_region_area": 100,
                    }
                )

                # Set the image
                sam.set_image(image_path)

                # Generate masks
                output_path = os.path.join(temp_dir, "output.tif")
                sam.generate(output=output_path)

                # Convert to GeoJSON format
                geojson_path = os.path.join(temp_dir, "output.geojson")
                sam.tiff_to_geojson(output_path, geojson_path)

                # Read the generated GeoJSON
                with open(geojson_path, 'r') as f:
                    geojson_data = json.load(f)

                # Filter by confidence threshold and add additional properties
                filtered_features = []
                for feature in geojson_data.get('features', []):
                    # Add confidence score (this would be based on your SAM-Geo output)
                    confidence = np.random.uniform(0.3, 1.0)  # Placeholder - replace with actual confidence from SAM-Geo
                    
                    if confidence >= confidence_threshold:
                        feature['properties']['confidence'] = confidence
                        feature['properties']['area'] = self._calculate_area(feature['geometry'])
                        filtered_features.append(feature)

                geojson_data['features'] = filtered_features
                return geojson_data

        except ImportError:
            logger.error("SAM-Geo not installed. Please install segment-geospatial package.")
            raise Exception("SAM-Geo not available. Please install segment-geospatial package.")
        except Exception as e:
            logger.error(f"Error in SAM-Geo processing: {str(e)}")
            raise e

    def _calculate_area(self, geometry: Dict[str, Any]) -> float:
        """
        Calculate area of a polygon geometry (simplified calculation)
        """
        try:
            from shapely.geometry import shape
            geom = shape(geometry)
            return geom.area
        except Exception:
            return 0.0

    @action(detail=False, methods=['post'])
    def upload_and_detect(self, request):
        """
        Upload image and immediately start object detection
        """
        # First create the geospatial image
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            geospatial_image = serializer.save(user=request.user)
            
            # Immediately start object detection
            detection_request = request.data.copy()
            detection_response = self.detect_objects(request, pk=geospatial_image.pk)
            
            return detection_response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ObjectDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing object detection results"""
    serializer_class = ObjectDetectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ObjectDetection.objects.filter(geospatial_image__user=self.request.user)


