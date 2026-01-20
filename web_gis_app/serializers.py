from shared.serializers import BaseModelSerializer

from .models import Dataset, DatasetFile, DatasetNode


class DatasetNodeSerializer(BaseModelSerializer):
    class Meta:
        model = DatasetNode
        fields = "__all__"


class DatasetSerializer(BaseModelSerializer):
    class Meta:
        model = Dataset
        fields = "__all__"


class DatasetFileSerializer(BaseModelSerializer):
    class Meta:
        model = DatasetFile
        fields = "__all__"
