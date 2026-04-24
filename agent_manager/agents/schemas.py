import operator
from enum import StrEnum
from typing import Annotated, TypedDict

from langchain.messages import AnyMessage
from pydantic import BaseModel


class UIActionType(StrEnum):
    MAP_ZOOM_TO = "map_zoom_to"


class MapZoomToPayload(TypedDict):
    longitude: float
    latitude: float


class UIAction(TypedDict):
    app: str
    type: str
    payload: dict | MapZoomToPayload


class RoutingDecision(BaseModel):
    next_node: str | None
    response: str


class Node(StrEnum):
    ORCHESTRATOR = "orchestrator"
    WEB_GIS_EXPERT = "web_gis_expert"
    UI_EXPERT = "ui_expert"
    MAP_ZOOM_TO = "map_zoom_to"


class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: str
    prev_node: str | None
    next_node: str | None
    final_response: str | list[str | dict]
    ui_action: UIAction
    geocode_result: dict | None
