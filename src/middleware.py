"""Application middleware for request ids and metrics."""

from __future__ import annotations

import time
import uuid
import logging
from typing import Callable, Awaitable

from fastapi import HTTPException, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import REQUEST_ID_CONTEXT


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request carries an id for tracing/logging."""

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:  # type: ignore[override]
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(  # type: ignore[override]
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = request_id
        token = REQUEST_ID_CONTEXT.set(request_id)

        try:
            response = await call_next(request)
        finally:
            REQUEST_ID_CONTEXT.reset(token)

        response.headers[self.header_name] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Tracks Prometheus metrics and logs each request."""

    def __init__(
        self,
        app,
        request_counter: Counter,
        request_latency: Histogram,
        error_counter: Counter,
    ) -> None:  # type: ignore[override]
        super().__init__(app)
        self.request_counter = request_counter
        self.latency_histogram = request_latency
        self.error_counter = error_counter
        self.logger = logging.getLogger("microtrace.request")

    async def dispatch(  # type: ignore[override]
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        method = request.method
        path = request.url.path
        status_code = 500
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except HTTPException as exc:
            status_code = exc.status_code
            self.error_counter.labels(
                method=method, path=path, exception=exc.__class__.__name__
            ).inc()
            raise
        except Exception as exc:
            self.error_counter.labels(
                method=method, path=path, exception=exc.__class__.__name__
            ).inc()
            raise
        finally:
            elapsed = time.perf_counter() - start
            self.request_counter.labels(
                method=method, path=path, status=str(status_code)
            ).inc()
            self.latency_histogram.labels(method=method, path=path).observe(elapsed)
            self.logger.info(
                "request_completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "elapsed_ms": round(elapsed * 1000, 3),
                },
            )
