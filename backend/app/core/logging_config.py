"""Centralised, enterprise-grade logging configuration.

- Console handler (always) plus size-rotated file handler (optional).
- JSON formatter for production log aggregation, compact human format in dev.
- A dedicated rotating audit file fed by the ``fyndo.audit`` logger.
- A context filter that stamps request id / user id / client ip on every record.
"""
import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.config import settings
from app.core.context import client_ip_var, request_id_var, user_id_var

_RESERVED = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime",
})

_CONFIGURED = False


class ContextFilter(logging.Filter):
    """Injects request-scoped identifiers onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        record.client_ip = client_ip_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Serialises each record as a single JSON object (one line per log)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "client_ip": getattr(record, "client_ip", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload.setdefault(key, value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Compact, readable single-line format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, '%H:%M:%S')} [{record.levelname:<7}] "
            f"{record.name} rid={getattr(record, 'request_id', '-')} "
            f"uid={getattr(record, 'user_id', '-')}: {record.getMessage()}"
        )
        extras = [
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        ]
        if extras:
            base = f"{base} | {' '.join(extras)}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def _build_formatter() -> logging.Formatter:
    return JsonFormatter() if settings.log_json else HumanFormatter()


def _rotating_handler(path: str, formatter: logging.Formatter, level: int) -> logging.Handler:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    handler.addFilter(ContextFilter())
    return handler


def configure_logging() -> None:
    """Idempotently configures application logging. Safe to call repeatedly."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)
    formatter = _build_formatter()
    context_filter = ContextFilter()

    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)
    console.addFilter(context_filter)
    root.addHandler(console)

    if settings.LOG_TO_FILE:
        log_dir = os.path.abspath(settings.LOG_DIR)
        root.addHandler(
            _rotating_handler(os.path.join(log_dir, settings.LOG_FILE_NAME), formatter, level)
        )
        logging.getLogger("fyndo.audit").addHandler(
            _rotating_handler(
                os.path.join(log_dir, settings.AUDIT_FILE_NAME), formatter, logging.INFO
            )
        )

    # Access logging is replaced by our own structured request middleware.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "multipart", "python_multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    logging.getLogger("fyndo.main").info(
        "Logging configured (level=%s, format=%s, to_file=%s).",
        logging.getLevelName(level),
        "json" if settings.log_json else "text",
        settings.LOG_TO_FILE,
    )
