from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import InventoryItem, ItemImage, Shop
from ..serializers import (
    ConfirmImageRequestSerializer,
    InventoryItemSerializer,
    ItemImageSerializer,
    PresignImageRequestSerializer,
)
from ..services.images import delete_object, presign_put


class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    Owner-scoped CRUD on inventory items, plus image actions.
    """

    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            InventoryItem.objects.filter(user=self.request.user)
            .select_related("shop", "category")
            .prefetch_related("images")
        )

    def perform_create(self, serializer):
        shop = Shop.objects.filter(user=self.request.user).first()
        if not shop:
            raise ValidationError("Create your shop before adding items.")
        serializer.save(user=self.request.user, shop=shop)

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        item = self.get_object()
        item.stale_at = timezone.now() + timedelta(days=30)
        item.save(update_fields=["stale_at", "updated_at"])
        return Response({"stale_at": item.stale_at})

    @action(detail=True, methods=["post"], url_path="images/presign")
    def presign_image(self, request, pk=None):
        item = self.get_object()
        serializer = PresignImageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = presign_put(item.id, serializer.validated_data["content_type"])
        return Response(result)

    @action(detail=True, methods=["post"], url_path="images/confirm")
    def confirm_image(self, request, pk=None):
        item = self.get_object()
        serializer = ConfirmImageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # If this is the first image or marked primary, demote any existing primary.
        is_primary = serializer.validated_data["is_primary"] or not item.images.exists()
        if is_primary:
            item.images.filter(is_primary=True).update(is_primary=False)

        next_position = (
            item.images.order_by("-position").values_list("position", flat=True).first()
        )
        position = (next_position or 0) + 1 if next_position is not None else 0

        image = ItemImage.objects.create(
            item=item,
            s3_key=serializer.validated_data["key"],
            width=serializer.validated_data["width"],
            height=serializer.validated_data["height"],
            position=position,
            is_primary=is_primary,
        )
        # Day 05 wires the Celery variant task here.
        return Response(
            ItemImageSerializer(image).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"images/(?P<image_id>[0-9a-f-]{36})",
    )
    def delete_image(self, request, pk=None, image_id=None):
        item = self.get_object()
        try:
            image = item.images.get(pk=image_id)
        except ItemImage.DoesNotExist as exc:
            raise NotFound("Image not found.") from exc

        delete_object(image.s3_key)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
