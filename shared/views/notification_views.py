from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models.notification_models import Notification
from ..serializers import BulkUpdateNotificationsSerializer, NotificationSerializer
from . import BaseModelViewSet


class NotificationViewSet(BaseModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .order_by("-created_at")
        )

    @action(
        detail=False,
        methods=["patch"],
        url_path="bulk",
        serializer_class=BulkUpdateNotificationsSerializer,
    )
    def bulk(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = self.get_queryset()
        if ids := serializer.validated_data.get("ids"):
            queryset = queryset.filter(id__in=ids)

        queryset.update(seen=serializer.validated_data["seen"])

        return Response(
            {
                "message": f"Seen updated for all the notifications to {serializer.validated_data['seen']}"
            }
        )
