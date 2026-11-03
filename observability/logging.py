"""Structured JSON logging. Sensitive values are sanitized before serialization."""
import json
import logging
import logging.handlers
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from .config import ObservabilityConfig
from .context import get_context
from .redaction import redact_mapping

FIELDS = ("timestamp", "level", "service", "environment", "correlation_id", "investigation_id", "request_type", "issue_key", "actor_type", "component", "operation", "tool", "status", "duration_ms", "result_count", "error_type", "error_code", "log_type", "message")


class JsonFormatter(logging.Formatter):
    def __init__(self, config):
        super().__init__()
        self.config = config

    def format(self, record):
        context = get_context()
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname, "service": self.config.service, "environment": self.config.environment,
            "message": record.getMessage(),
        }
        if context:
            event.update(context.as_dict())
        for field in FIELDS:
            if field in record.__dict__ and record.__dict__[field] is not None:
                event[field] = record.__dict__[field]
        if self.config.redact_sensitive_data:
            event = redact_mapping(event)
        return json.dumps(event, ensure_ascii=False, separators=(",", ":"))


class LokiHandler(logging.Handler):
    def __init__(self, url, config):
        super().__init__()
        self.url, self.config = url.rstrip("/"), config
        self.setFormatter(JsonFormatter(config))

    def emit(self, record):
        try:
            payload = {"streams": [{"stream": {"service": self.config.service, "environment": self.config.environment, "level": record.levelname}, "values": [[str(time.time_ns()), self.format(record)]]}]}
            request = Request(self.url + "/loki/api/v1/push", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=2):
                pass
        except Exception:
            self.handleError(record)


def configure_logging(config=None, *, stream=None):
    config = config or ObservabilityConfig.from_env()
    root = logging.getLogger("psi")
    root.handlers.clear()
    root.setLevel(getattr(logging, config.level, logging.INFO))
    formatter = JsonFormatter(config)
    destinations = {part.strip() for part in config.destination.split(",") if part.strip()}
    if not destinations:
        destinations = {"stdout"}
    if "stdout" in destinations:
        handler = logging.StreamHandler(stream or sys.stdout)
        handler.setFormatter(formatter); root.addHandler(handler)
    if "file" in destinations or config.log_file:
        handler = logging.handlers.WatchedFileHandler(config.log_file or "events.jsonl")
        handler.setFormatter(formatter); root.addHandler(handler)
    if "loki" in destinations or config.loki_url:
        if config.loki_url:
            root.addHandler(LokiHandler(config.loki_url, config))
    if config.log_raw_evidence:
        root.warning("raw evidence logging enabled; secrets remain redacted", extra={"component": "startup", "operation": "configuration_warning"})
    return root


def get_logger(name):
    return logging.getLogger("psi." + name)


# Library imports must remain quiet until the host explicitly configures logging.
_default_logger = logging.getLogger("psi")
_default_logger.addHandler(logging.NullHandler())
_default_logger.propagate = False
