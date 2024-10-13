from requests import Session


class WeatherAPI(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = ""

    def request(
        self, method, url, params=None, data=None, headers=None, *args, **kwargs
    ):

        return super().request(
            method, url, params=None, data=None, headers=None, *args, **kwargs
        )
