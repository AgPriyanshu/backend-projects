import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request) -> Any:
        start_time = time.time()

        # Structure request logging
        request_data = {
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.GET),
            "body": request.body.decode() if request.body else None,
        }
        logger.info("Request received", extra={"request_data": request_data})

        response = self.get_response(request)
        duration = time.time() - start_time

        # Structure response logging
        try:
            response_body = json.loads(response.content.decode())
        except:
            response_body = response.content.decode()

        response_data = {
            "status_code": response.status_code,
            "duration": f"{duration:.2f}s",
            "body": response_body,
        }
        logger.info("Response sent", extra={"response_data": response_data})

        return response
