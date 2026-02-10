import json

import redis
from django.conf import settings
from django.contrib.auth.models import User

from shared.constants import AppName

from .models import Notification
from .serializers import NotificationSerializer
from .utils.redis import get_notifications_channel


class NotificationManager:
    _redis_client = redis.from_url(
        settings.CACHES["default"]["LOCATION"],
        decode_responses=True,
    )
    _serializer = NotificationSerializer

    @classmethod
    def send_message(cls, content: str, app_name: AppName, user: User):
        notification = Notification.objects.create(
            content=content, app_name=app_name.value, user=user
        )
        serializer = cls._serializer(instance=notification)
        channel = get_notifications_channel(user)
        cls._redis_client.publish(channel, json.dumps({**serializer.data}))


notification_manager = NotificationManager()


# Convenience function.
def send_notification(content: str, app_name: AppName, user: User):
    notification_manager.send_message(content, app_name, user)
