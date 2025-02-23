from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from shared.views import BaseModelViewSet

from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer


class MessagesViewSet(BaseModelViewSet):
    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer


class ChatRoomsViewSet(ModelViewSet):
    queryset = ChatRoom.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer
