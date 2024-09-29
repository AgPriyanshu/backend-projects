import json
from rest_framework.renderers import JSONRenderer
from rest_framework import status

class CustomJSONRenderer(JSONRenderer):
    charset= 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response', None)

        # Building the custom response structure
        response_data = {
            "meta": {
                "status_code": response.status_code if response else status.HTTP_200_OK,
                "success": response.status_code < status.HTTP_400_BAD_REQUEST if response else True
            },
            "data": data
        }

        # Return serialized JSON data
        return json.dumps(response_data)