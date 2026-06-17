import logging
import os
import re

from pythonjsonlogger.json import JsonFormatter

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_REDACTED = "Bearer ***REDACTED***"

_SENSITIVE_HEADERS = {"authorization", "x-safetyculture-token", "x-api-key"}

# LogRecord attributes that belong to the stdlib — mutating these can break
# the formatter, so we only scan extra fields added by application code.
_STDLIB_RECORD_ATTRS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class _SensitiveFilter(logging.Filter):
    """
    Two-layer redaction applied to every log record:

    1. Header dict field — any record carrying a ``headers`` extra field has
       Authorization / x-safetyculture-token / x-api-key values replaced with
       ***REDACTED*** before the record is serialised.

    2. Bearer token strings — any string-valued extra field (and the log
       message itself) that contains a ``Bearer <token>`` pattern has the
       token portion replaced so raw tokens never appear in log output even
       when accidentally interpolated into a message.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # ── 1. Header dict redaction ──────────────────────────────────────────
        headers = getattr(record, "headers", None)
        if isinstance(headers, dict):
            record.headers = {
                k: ("***REDACTED***" if k.lower() in _SENSITIVE_HEADERS else v)
                for k, v in headers.items()
            }

        # ── 2. Bearer token redaction in message and extra string fields ──────
        if isinstance(record.msg, str) and "Bearer" in record.msg:
            record.msg = _BEARER_RE.sub(_REDACTED, record.msg)

        for key, val in record.__dict__.items():
            if key in _STDLIB_RECORD_ATTRS:
                continue
            if isinstance(val, str) and "Bearer" in val:
                setattr(record, key, _BEARER_RE.sub(_REDACTED, val))

        return True


def configure_logging(level: str | None = None) -> None:
    """
    Configure root logger with JSON output.
    Level is read from LOG_LEVEL env var, then the ``level`` arg, defaulting to INFO.
    Safe to call multiple times — clears existing handlers first (idempotent).
    """
    resolved = os.environ.get("LOG_LEVEL", level or "INFO").upper()

    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    )
    handler.addFilter(_SensitiveFilter())

    root = logging.getLogger()
    root.setLevel(resolved)
    root.handlers = []
    root.addHandler(handler)
