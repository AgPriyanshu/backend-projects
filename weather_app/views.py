from rest_framework.decorators import api_view
from rest_framework.response import Response

from .helpers import get_current_ist_date
from .weather_api import weather_api_session


@api_view(["GET"])
def current(request, location: str):
    weather_api_url = ""
    if location:
        weather_api_url += location

    date = get_current_ist_date()
    weather_api_url += "/" + date
    response = weather_api_session.request(url=weather_api_url, method="GET")
    return Response(
        {
            "message": f"Current weather for location: {location} ",
            "data": response.json(),
        }
    )
