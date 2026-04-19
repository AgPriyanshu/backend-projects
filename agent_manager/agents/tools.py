from geopy.geocoders import Nominatim
from langchain_core.tools import tool

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
