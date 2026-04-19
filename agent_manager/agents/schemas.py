from enum import StrEnum
from typing import TypedDict


class UIActionType(StrEnum):
    MAP_ZOOM_TO = "map_zoom_to"


class MapZoomToPayload(TypedDict):
    longitude: float
    latitude: float


class UIAction(TypedDict):
    app: str
    type: str
    payload: dict | MapZoomToPayload
