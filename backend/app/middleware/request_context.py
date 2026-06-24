"""
Request Context Middleware
----------------------------
ASGI middleware that attaches a unique request ID and timing context
to every incoming request. Useful for:
    - Correlating log entries across services
    - Measuring request latency
    - Audit trails

The request ID is also returned in the X-Request-ID response header.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Injects request_id and timing into each request's state.
    Logs request duration on completion.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        start_time = time.perf_counter()

        # Attach to request state for downstream use
        request.state.request_id = request_id
        request.state.start_time = start_time

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "REQUEST_ERROR | id=%s method=%s path=%s duration_ms=%.2f",
                request_id, request.method, request.url.path, duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Log request completion (skip health checks to reduce noise)
        if request.url.path not in ("/health", "/"):
            logger.info(
                "REQUEST | id=%s method=%s path=%s status=%d duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds standard security headers to every response.
    Defence-in-depth against common web attacks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
