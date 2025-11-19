import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.time()

        # Log request.
        # logger.debug(
        #     f"Request: {request.method} {request.path} - Headers: {dict(request.headers)}"
        # )

        response = self.get_response(request)

        # Calculate duration
        time.time() - start_time

        # Log response
        # logger.debug(
        #     f"Response: {request.method} {request.path} - Status: {response.status_code} - Duration: {duration:.2f}s"
        # )

        return response
