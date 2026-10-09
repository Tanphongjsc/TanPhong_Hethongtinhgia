"""Consistent technical logs with request correlation and secret redaction."""
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import os
import re
from urllib.parse import unquote, urlsplit

request_trace = ContextVar("costing_request_trace", default=None)


def redact(value):
    text = str(value)
    secrets = [os.environ.get(key, "") for key in ("DJANGO_SECRET_KEY", "DB_PASSWORD", "DATABASE_URL")]
    try:
        password = urlsplit(os.environ.get("DATABASE_URL", "")).password or ""
        secrets.extend((password, unquote(password)))
    except ValueError:
        pass
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)\bpostgres(?:ql)?://[^\s\"']+", "postgresql://[REDACTED]", text)
    return re.sub(r"(?i)\b(password|secret_key|authorization|token|api_key)\s*[:=]\s*(?:'[^']*'|\"[^\"]*\"|\S+)", r"\1=[REDACTED]", text)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname, "logger": record.name, "message": redact(record.getMessage()),
            "environment": os.environ.get("APP_ENV", "development")}
        trace = getattr(record, "trace_id", None) or request_trace.get()
        if trace: payload["trace_id"] = str(trace)
        for key in ("run_id", "scenario_id", "stage", "method", "path", "status", "duration_ms"):
            if hasattr(record, key):
                value = getattr(record, key)
                payload[key] = redact(value) if isinstance(value, str) else value
        if record.exc_info: payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)
