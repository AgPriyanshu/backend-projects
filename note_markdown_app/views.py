from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Note
from .serializers import NoteSerializer


class NotesViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
