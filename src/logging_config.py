"""Central logging configuration for MicroTrace."""

from __future__ import annotations

import contextvars
import logging
import sys
from typing import Final

from pythonjsonlogger import jsonlogger

# Context variable used to enrich logs with the active request id.
REQUEST_ID_CONTEXT: Final[contextvars.ContextVar[str]] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Injects the current request id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.request_id = REQUEST_ID_CONTEXT.get()
        return True


def configure_logging() -> None:
    """
    Configure the root logger for structured JSON output.

    This function is idempotent so it can be called safely on import/reload.
    """

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
