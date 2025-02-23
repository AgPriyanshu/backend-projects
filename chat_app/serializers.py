from shared.serializers import BaseModelSerializer

from .models import ChatRoom, Message


class MessageSerializer(BaseModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"


class ChatRoomSerializer(BaseModelSerializer):
    class Meta:
        model = ChatRoom
        fields = "__all__"
