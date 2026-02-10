from django.contrib.auth.models import User
from django.db import models

from shared.models.base_models import BaseModel


class Message(BaseModel):
    content = models.TextField()


class ChatRoom(BaseModel):
    name = models.TextField()
    user = None
    messages = models.ManyToManyField(Message, related_name="chatroom")
    sender = models.ForeignKey(
        User, related_name="chat_room_sender", on_delete=models.DO_NOTHING
    )
    receiver = models.ForeignKey(
        User, related_name="chat_room_receiver", on_delete=models.DO_NOTHING
    )
