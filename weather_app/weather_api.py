from urllib import parse

from requests import Session

from .constants import WEATHER_API

VISUAL_CROSSING_API_KEY = "9XE8DJQ84C9EQD2F93AL3WY95"


class WeatherAPI(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = WEATHER_API

    def request(
        self, method, url, params=None, data=None, headers=None, *args, **kwargs
    ):
        url = parse.urljoin(self.base_url, url)
        if params:
            params = {**params}
        else:
            params = {}
        params = {**params, "key": VISUAL_CROSSING_API_KEY}
        return super().request(method, url, params, data, headers, *args, **kwargs)


weather_api_session = WeatherAPI()
