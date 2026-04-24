import operator
from enum import StrEnum
from typing import Annotated, Any, NotRequired, TypedDict

from langchain.messages import AnyMessage
from pydantic import BaseModel


class UIActionType(StrEnum):
    MAP_ZOOM_TO = "map_zoom_to"
    OPEN_PROCESSING_TOOL = "open_processing_tool"


class MapZoomToPayload(TypedDict):
    longitude: float
    latitude: float


class OpenProcessingToolPayload(TypedDict):
    tool_name: str
    defaults: dict[str, Any]
    output_name: NotRequired[str]


class UIAction(TypedDict):
    app: str
    type: str
    payload: dict | MapZoomToPayload | OpenProcessingToolPayload


class RoutingDecision(BaseModel):
    next_node: str | None
    response: str


class Node(StrEnum):
    ORCHESTRATOR = "orchestrator"
    WEB_GIS_EXPERT = "web_gis_expert"
    UI_EXPERT = "ui_expert"
    MAP_ZOOM_TO = "map_zoom_to"
    OPEN_PROCESSING_TOOL = "open_processing_tool"


class LoadedLayer(TypedDict):
    id: str
    name: str
    type: str
    dataset_id: NotRequired[str]


class PendingProcessingTool(TypedDict):
    tool_name: str
    defaults: dict[str, Any]


class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: str
    prev_node: str | None
    next_node: str | None
    final_response: str | list[str | dict]
    ui_action: UIAction
    geocode_result: dict | None
    loaded_layers: list[LoadedLayer]
    pending_processing_tool: PendingProcessingTool | None
