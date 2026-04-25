from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.views import BaseModelViewSet

from .models import Character, Stat
from .serializers import CharacterCreateSerializer, CharacterSerializer, StatSerializer


class CharacterViewSet(BaseModelViewSet):
    queryset = Character.objects.all()
    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().prefetch_related("stats")

    def get_serializer_class(self):
        if self.action == "create":
            return CharacterCreateSerializer
        return CharacterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        character = Character.objects.prefetch_related("stats").get(
            pk=serializer.instance.pk
        )
        return Response(CharacterSerializer(character).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="stats")
    def add_stat(self, request, pk=None):
        """Add a new stat to the given character."""
        character = self.get_object()
        serializer = StatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(character=character, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StatViewSet(BaseModelViewSet):
    queryset = Stat.objects.all()
    serializer_class = StatSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "delete", "head", "options"]
