from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.views import BaseModelViewSet

from .models import Note
from .serializers import NoteSerializer


class NotesViewSet(BaseModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
