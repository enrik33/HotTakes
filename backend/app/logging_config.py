"""
Structured logging configuration for API and background jobs.
"""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

REQUEST_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class JsonFormatter(logging.Formatter):
    """Format log records as a compact JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", "app"),
            "event": getattr(record, "event", record.getMessage()),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", REQUEST_ID_CTX.get()),
            "job_name": getattr(record, "job_name", None),
        }
        for key in ("method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger to emit structured JSON logs."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Replace default handlers to guarantee consistent format.
    root_logger.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str, component: str) -> logging.LoggerAdapter:
    """Create logger adapter with default component field."""
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {"component": component})
