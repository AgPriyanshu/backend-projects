from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import Shop
from ..serializers import ShopSerializer, ShopWithDistanceSerializer


class ShopViewSet(viewsets.ViewSet):
    """
    POST   /dead-stock/shops/            create (auth, one-per-user)
    GET    /dead-stock/shops/me/         owner's shop
    PATCH  /dead-stock/shops/me/         update owner's shop
    GET    /dead-stock/shops/{id}/       public retrieve
    GET    /dead-stock/shops/nearby/     public radius search
    """

    def get_permissions(self):
        if self.action in ("retrieve", "nearby"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request):
        if Shop.objects.filter(user=request.user).exists():
            raise ValidationError(
                "Shop already exists for this user.", code="already_exists"
            )
        serializer = ShopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = Shop.objects.create(user=request.user, **serializer.validated_data)
        return Response(
            ShopSerializer(shop).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        try:
            shop = Shop.objects.get(pk=pk)
        except Shop.DoesNotExist as exc:
            raise NotFound("Shop not found.") from exc
        return Response(ShopSerializer(shop).data)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        shop = Shop.objects.filter(user=request.user).first()
        if not shop:
            raise NotFound("You don't have a shop yet.")

        if request.method == "GET":
            return Response(ShopSerializer(shop).data)

        serializer = ShopSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for k, v in serializer.validated_data.items():
            setattr(shop, k, v)
        shop.save()
        return Response(ShopSerializer(shop).data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def nearby(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError) as exc:
            raise ValidationError("lat and lng are required floats.") from exc

        radius_km = float(request.query_params.get("radius_km", 5))
        limit = min(int(request.query_params.get("limit", 20)), 100)

        point = Point(lng, lat, srid=4326)
        qs = (
            Shop.objects.annotate(distance=Distance("location", point))
            .filter(location__dwithin=(point, D(km=radius_km)))
            .order_by("distance")[:limit]
        )
        return Response(
            {"shops": ShopWithDistanceSerializer(qs, many=True).data}
        )
