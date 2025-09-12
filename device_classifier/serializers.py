from rest_framework.fields import ImageField
from rest_framework.serializers import Serializer


class DeviceClassifierSerializer(Serializer):
    device = ImageField(max_length=None, allow_empty_file=False, required=True)
