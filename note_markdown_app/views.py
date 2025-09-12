import markdown
from django.http.response import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.views import BaseModelViewSet

from .grammar_tool import get_tool
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

    @action(methods=["POST"], detail=True, url_path="grammar-check")
    def grammar_check(self, request, pk=None):
        note = self.get_object()

        with note.content.open("r") as file:
            text = file.read()

        matches = get_tool().check(text)
        grammar_corrections = []

        for match in matches:
            grammar_corrections.append(
                {
                    "ruleId": match.ruleId,
                    "message": match.message,
                    "replacements": match.replacements,
                }
            )

        return Response({"corrections": grammar_corrections}, status=status.HTTP_200_OK)
