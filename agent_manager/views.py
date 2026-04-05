from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from shared.views import BaseModelViewSet

from .models import LLM, ChatSession
from .serializers import ChatSessionSerializer, LLMSerializer


class ChatSessionViewSet(BaseModelViewSet):
    queryset = ChatSession.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSessionSerializer


class LLMViewSet(viewsets.ModelViewSet):
    queryset = LLM.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LLMSerializer
