from typing import Any, Literal

from pydantic import BaseModel

from agent_manager.agents.base import BaseExpert
from agent_manager.agents.registry import ExpertRegistry

# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------

class WebGISAction(BaseModel):
    action_type: Literal[
        "load_dataset", "remove_layer", "fit_to_layer", "toggle_visibility", "none"
    ]
    dataset_name: str | None = None


class WebGISActionPlan(BaseModel):
    actions: list[WebGISAction]


# ---------------------------------------------------------------------------
# Expert
# ---------------------------------------------------------------------------

class WebGISExpert(BaseExpert):
    """Expert for Web GIS / mapping operations."""

    @property
    def name(self) -> str:
        return "web_gis"

    @property
    def description(self) -> str:
        return (
            "Handles questions about maps, geospatial data, GIS layers, "
            "raster/vector datasets, tile rendering, and any Web GIS functionality."
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are a Web GIS expert. Answer only the user's Web GIS "
            "question with a concise, accurate explanation."
        )

    def get_action_schema(self) -> type[BaseModel]:
        return WebGISActionPlan

    def _build_action_extraction_prompt(self) -> str:
        return (
            "You are a Web GIS assistant. Analyze the user's request and identify any map actions to perform.\n\n"
            "Available actions:\n"
            "- load_dataset: User wants to load/show/display a dataset on the map. Extract the dataset_name.\n"
            "- remove_layer: User wants to remove/hide a layer from the map. Extract the dataset_name.\n"
            "- fit_to_layer: User wants to zoom or fit the map to a specific layer. Extract the dataset_name.\n"
            "- toggle_visibility: User wants to toggle a layer's visibility. Extract the dataset_name.\n"
            "- none: The request is purely informational — no map action needed.\n\n"
            "Return all applicable actions. Use 'none' only when no map action is requested."
        )

    def _extract_actions(self, action_plan: BaseModel) -> list[dict[str, Any]]:
        if not isinstance(action_plan, WebGISActionPlan):
            return []

        return [
            {
                "app": self.name,
                "action_type": action.action_type,
                "payload": {"dataset_name": action.dataset_name},
            }
            for action in action_plan.actions
            if action.action_type != "none"
        ]


# Auto-register on import.
ExpertRegistry.register(WebGISExpert())
