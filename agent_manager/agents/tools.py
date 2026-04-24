from typing import Annotated, Any

from geopy.geocoders import Nominatim
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

_geocoder = Nominatim(user_agent="atlas-platform")


@tool
def geocode(query: str) -> dict:
    """Geocode a place name or address and return its coordinates."""
    location = _geocoder.geocode(query)

    if location is None:
        return {"error": f"Could not find coordinates for '{query}'."}

    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "address": location.address,
    }


@tool
def map_zoom_to(latitude: float, longitude: float) -> dict:
    """Zoom the map to the given coordinates. Use this after geocoding when the user wants to navigate or fly to a location."""
    return {"latitude": latitude, "longitude": longitude}


@tool
def list_loaded_vector_layers(
    state: Annotated[dict, InjectedState],
) -> list[dict]:
    """List vector layers currently loaded on the user's map.

    Use this to resolve a user's layer reference (e.g. "the buildings layer")
    to a concrete dataset id before invoking a processing tool.
    Returns a list of objects with id, name, type, and dataset_id.
    """
    layers = state.get("loaded_layers") or []

    return [layer for layer in layers if layer.get("type") == "vector"]


@tool
def list_processing_tools() -> list[dict]:
    """List the geoprocessing tools available in the Web GIS processing toolbox.

    Use this before opening a processing tool so you know the exact tool_name
    and the parameter names, types, and defaults you must supply.
    """
    from web_gis_app.tool_registry import list_tools

    return list_tools()


@tool
def open_processing_tool(
    tool_name: str,
    defaults: dict[str, Any],
    output_name: str | None = None,
) -> dict:
    """Open a geoprocessing tool modal on the frontend with inputs prefilled.

    Call this when the user wants to run a processing workflow (buffer, clip,
    dissolve, centroid, simplify, convex hull, hillshade, slope, contour, etc.).
    Do not call it until you have:
      1. Found the tool_name via list_processing_tools.
      2. Resolved any input layer references to dataset ids via list_loaded_vector_layers.
      3. Collected every required parameter from the user (or set a reasonable default).

    Args:
        tool_name: The exact tool name as returned by list_processing_tools (toolName field).
        defaults: A dict of prefilled form values. Must include "inputDatasetId" and any
            tool-specific parameters (e.g. {"inputDatasetId": "...", "distance": 50, "units": "meters"}).
        output_name: Optional name for the output dataset.
    """
    payload: dict[str, Any] = {"tool_name": tool_name, "defaults": defaults}

    if output_name:
        payload["output_name"] = output_name

    return payload
