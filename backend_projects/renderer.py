import json

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class CustomJSONRenderer(JSONRenderer):
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)
        message = ""
        response_data_body = {}
        if isinstance(data, dict):
            response_data_body = data.get("data", data)
            message = data.get("message", "")
        else:
            response_data_body = data
        # Building the custom response structure
        response_data = {
            "meta": {
                "status_code": response.status_code if response else status.HTTP_200_OK,
                "success": (
                    response.status_code < status.HTTP_400_BAD_REQUEST
                    if response
                    else True
                ),
                "message": message,
            },
            "data": response_data_body,
        }

        # Return serialized JSON data using DRF's encoder
        return json.dumps(response_data, cls=JSONEncoder, ensure_ascii=False)
