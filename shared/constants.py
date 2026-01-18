from enum import StrEnum


class BaseEnum(StrEnum):
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]
