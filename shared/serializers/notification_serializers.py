from rest_framework import serializers

from ..models.notification_models import Notification
from .base_serializer import BaseModelSerializer


class NotificationSerializer(BaseModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class BulkUpdateNotificationsSerializer(serializers.Serializer):
    seen = serializers.BooleanField(required=True)
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
