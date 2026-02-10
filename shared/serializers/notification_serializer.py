from ..models.notification_models import Notification
from .base_serializer import BaseModelSerializer


class NotificationSerializer(BaseModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
