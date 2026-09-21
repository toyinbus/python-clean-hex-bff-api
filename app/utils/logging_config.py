"""Application logging setup (generic, reusable library layer).

Two output modes, selected by config so the same code ships everywhere:

  * ``console`` — human-readable single line, for local development.
  * ``json``    — one JSON object per line, ready to ship to CloudWatch /
                  Elastic / Loki with no extra parser (production).

Every record is stamped with the request id from the request-context ContextVar,
so logs correlate with the ``request_id`` returned in each response envelope.
Uvicorn's own loggers are routed through the same handler so ALL output — app
logs and access/error logs — shares one format.

Uses only the standard library (no extra dependency).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.utils.request_context import get_request_id

_FRAMEWORK_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi")

_RESET = "\033[0m"
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[1;37;41m",  # bold white on red
}


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record (empty -> '-')."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        # Structured tags attached via `extra=` (from response_error / access log).
        for key in (
            "status", "code", "http_method", "path", "latency_ms",
            "request_body", "response_body",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter; colorizes the level tag when on a TTY."""

    def __init__(self, *, use_color: bool) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname_tag)s %(name)s [%(request_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        tag = f"{record.levelname:<8}"
        if self._use_color:
            color = _LEVEL_COLORS.get(record.levelname, "")
            if color:
                tag = f"{color}{tag}{_RESET}"
        record.levelname_tag = tag
        return super().format(record)


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    """Install one root handler and route framework loggers through it.

    Call once, as early as possible (top of ``create_app``). Safe to call again;
    it resets the root handlers each time.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        # Colorize the level tag only on a real terminal, so piped/redirected
        # output (and log files) stay free of ANSI escape codes.
        handler.setFormatter(ConsoleFormatter(use_color=sys.stdout.isatty()))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Let framework loggers bubble up to the single root handler (one format).
    for name in _FRAMEWORK_LOGGERS:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
