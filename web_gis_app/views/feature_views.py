from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models.feature_models import Feature
from ..serializers.feature_serializers import FeatureSerializer


class FeatureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual GeoJSON Features mapped to PostGIS.
    Provides dataset filtering implicitly.
    """

    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["dataset"]

    def get_queryset(self):
        return Feature.objects.filter(dataset__dataset_node__user=self.request.user)

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        if not is_many:
            return super().create(request, *args, **kwargs)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
