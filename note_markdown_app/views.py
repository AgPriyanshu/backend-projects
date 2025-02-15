import markdown
from django.http.response import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from shared.views import BaseModelViewSet

from .models import Note
from .serializers import NoteSerializer


class NotesViewSet(BaseModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(methods=["GET"], detail=True, url_path="markdown-preview")
    def markdown_preview(self, request, pk=None):
        note = self.get_object()
        with note.content.open("r") as input_file:
            text = input_file.read()
            preview = markdown.markdown(text)

        return HttpResponse(preview, status=status.HTTP_200_OK)
