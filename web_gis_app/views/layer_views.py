from rest_framework.permissions import IsAuthenticated

from shared.views import BaseModelViewSet

from ..models.layer_models import Layer
from ..serializers import LayerSerializer


class LayerViewSet(BaseModelViewSet):
    queryset = Layer.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LayerSerializer
