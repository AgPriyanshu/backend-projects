from enum import StrEnum


class Role(StrEnum):
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class ChatMessageType(StrEnum):
    MESSAGE = "message"
    ACTION = "action"
    INTERRUPT = "interrupt"
