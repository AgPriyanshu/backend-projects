import json

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class CustomJSONRenderer(JSONRenderer):
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = None

        if renderer_context:
            response = renderer_context.get("response", None)

        if response and response.status_code == status.HTTP_204_NO_CONTENT:
            return b""

        message = ""
        response_data_body = {}

        if response and hasattr(response, "data") and isinstance(response.data, dict):
            message = response.data.pop("message", "")
            data = response.data

        if isinstance(data, dict):
            response_data_body = data.get("data", data)
        else:
            response_data_body = data

        response_data = {
            "meta": {
                "status_code": response.status_code if response else status.HTTP_200_OK,
                "success": response.status_code < status.HTTP_400_BAD_REQUEST
                if response
                else True,
                "message": message,
            },
            "data": response_data_body,
        }

        return json.dumps(response_data, cls=JSONEncoder, ensure_ascii=False)
