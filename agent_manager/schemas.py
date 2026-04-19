from dataclasses import dataclass
from enum import StrEnum


@dataclass
class ChatMessage:
    type: str
    message_id: str
    session_id: str
    message: str
    user_id: str
    role: str


class ChatMessageRole(StrEnum):
    USER = "user"
    AI = "ai"
    System = "system"
