from datetime import timedelta

from django.db import transaction
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
from ..tasks import generate_image_variants


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
        generate_image_variants.delay(str(image.id))
        return Response(
            ItemImageSerializer(image).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["patch"], url_path="images/reorder")
    def reorder_images(self, request, pk=None):
        item = self.get_object()
        ordered_ids = request.data.get("image_ids")
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError(
                {"image_ids": "Provide a non-empty list of image ids."}
            )

        images = list(item.images.filter(id__in=ordered_ids))
        if len(images) != len(ordered_ids):
            raise NotFound("One or more images were not found.")

        image_by_id = {str(image.id): image for image in images}
        with transaction.atomic():
            for index, image_id in enumerate(ordered_ids):
                image = image_by_id[str(image_id)]
                image.position = index + 1000
                image.save(update_fields=["position", "updated_at"])
            for index, image_id in enumerate(ordered_ids):
                image = image_by_id[str(image_id)]
                image.position = index
                image.save(update_fields=["position", "updated_at"])

        return Response(ItemImageSerializer(item.images.all(), many=True).data)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"images/(?P<image_id>[0-9a-f-]{36})",
    )
    def image_detail(self, request, pk=None, image_id=None):
        item = self.get_object()
        try:
            image = item.images.get(pk=image_id)
        except ItemImage.DoesNotExist as exc:
            raise NotFound("Image not found.") from exc

        if request.method == "PATCH":
            is_primary = request.data.get("is_primary")
            position = request.data.get("position")

            with transaction.atomic():
                if is_primary is not None:
                    if not isinstance(is_primary, bool):
                        raise ValidationError({"is_primary": "Expected a boolean."})
                    if is_primary:
                        item.images.exclude(pk=image.pk).update(is_primary=False)
                    image.is_primary = is_primary

                if position is not None:
                    if not isinstance(position, int) or position < 0:
                        raise ValidationError(
                            {"position": "Expected a non-negative integer."}
                        )
                    image.position = position

                image.save(update_fields=["is_primary", "position", "updated_at"])

            return Response(ItemImageSerializer(image).data)

        was_primary = image.is_primary
        delete_object(image.s3_key)
        image.delete()

        if was_primary:
            replacement = item.images.order_by("position").first()
            if replacement:
                replacement.is_primary = True
                replacement.save(update_fields=["is_primary", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)
