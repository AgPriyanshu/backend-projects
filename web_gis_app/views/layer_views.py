import json

from django.http import JsonResponse
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from shared.views import BaseModelViewSet

from ..models.layer_models import Layer
from ..serializers import LayerSerializer


class LayerViewSet(BaseModelViewSet):
    queryset = Layer.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LayerSerializer

    @action(methods=["GET"], detail=True, url_path="geojson", url_name="geojson")
    def geojson(self, request, pk=None):
        """
        Return the layer's features from PostGIS as a GeoJSON FeatureCollection.
        """
        layer = self.get_object()
        dataset = layer.source

        # Check if dataset has features.
        if not hasattr(dataset, "features"):
            return JsonResponse(
                {"type": "FeatureCollection", "features": []},
                safe=False,
            )

        features = []
        for feature in dataset.features.all():
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(feature.geometry.json),
                    "properties": feature.properties,
                }
            )

        return JsonResponse(
            {"type": "FeatureCollection", "features": features},
            safe=False,
        )
