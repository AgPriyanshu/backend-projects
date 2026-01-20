from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Dataset
from .serializers import DatasetSerializer


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        pass

    def create(self, request):
        serializer = self.get_serializer(request.data)
        serializer.validate(raise_exception=True)
