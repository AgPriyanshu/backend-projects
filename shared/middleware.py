import json
import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

from backend_projects.logger import logger


class LoggingMiddleware:
    """
    Middleware to log HTTP request and response details including:
    - Request method, path, headers, and body
    - Response status code, headers, and body
    - Request execution time
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        # Paths to exclude from detailed logging (to reduce noise)
        self.exclude_paths = ["/admin/jsi18n/", "/static/", "/media/"]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip logging for excluded paths
        if any(request.path.startswith(path) for path in self.exclude_paths):
            return self.get_response(request)

        start_time = time.time()

        # Log request details
        self._log_request(request)

        # Process the request
        response = self.get_response(request)

        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Log response details
        self._log_response(request, response, duration)

        return response

    def _log_request(self, request: HttpRequest) -> None:
        """Log incoming request details."""
        try:
            request_body = self._get_request_body(request)

            logger.info(
                f"→ {request.method} {request.path}",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "query_params": dict(request.GET),
                    "user": str(request.user)
                    if hasattr(request, "user")
                    else "Anonymous",
                    "ip": self._get_client_ip(request),
                },
            )

            # Log body only for methods that typically have a body
            if request_body and request.method in ["POST", "PUT", "PATCH"]:
                logger.debug(f"Request Body: {request_body}")

        except Exception as e:
            logger.warning(f"Error logging request: {e}")

    def _log_response(
        self, request: HttpRequest, response: HttpResponse, duration: float
    ) -> None:
        """Log outgoing response details."""
        try:
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO

            logger.log(
                log_level,
                f"← {request.method} {request.path} - {response.status_code} - {duration:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration, 2),
                },
            )

            # Log response body for non-2xx responses or in debug mode
            if response.status_code >= 400 or logger.isEnabledFor(logging.DEBUG):
                response_body = self._get_response_body(response)
                if response_body:
                    logger.debug(f"Response Body: {response_body}")

        except Exception as e:
            logger.warning(f"Error logging response: {e}")

    def _get_request_body(self, request: HttpRequest) -> str:
        """Extract and parse request body."""
        try:
            if request.content_type == "application/json" and request.body:
                body = json.loads(request.body.decode("utf-8"))
                return self._mask_sensitive_data(body)
            elif request.body:
                return request.body.decode("utf-8")[:500]  # Limit body size
        except Exception:
            return "<unable to parse body>"
        return ""

    def _get_response_body(self, response: HttpResponse) -> str:
        """Extract and parse response body."""
        try:
            if hasattr(response, "content") and response.content:
                content = response.content.decode("utf-8")
                # Try to parse as JSON for better formatting
                try:
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2)[:1000]  # Limit size
                except json.JSONDecodeError:
                    return content[:500]  # Limit size for non-JSON
        except Exception:
            return "<unable to parse response>"
        return ""

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _mask_sensitive_data(self, data: dict) -> dict:
        """Mask sensitive fields in request body."""
        sensitive_fields = ["password", "token", "secret", "api_key", "authorization"]
        masked_data = data.copy()

        for key in masked_data:
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                masked_data[key] = "***MASKED***"

        return masked_data
