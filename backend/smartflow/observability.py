import json
import logging
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

SAFE_FIELDS = {
    "job_id",
    "trace_id",
    "command_trace_id",
    "request_id",
    "stage",
    "code",
    "status",
    "attempt",
    "event_id",
    "duration_ms",
    "method",
    "route",
    "frames",
    "exception_type",
    "version",
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "event": record.msg,
                **getattr(record, "safe_fields", {}),
            },
            ensure_ascii=False,
        )


def create_logger(data_dir: Path, role="api"):
    directory = data_dir / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"smartflow.{data_dir}.{role}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        filename = "worker.jsonl" if role == "worker" else "runtime.jsonl"
        handler = RotatingFileHandler(
            directory / filename, maxBytes=2_000_000, backupCount=4, encoding="utf-8"
        )
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


def emit(logger, event: str, **fields):
    logger.info(event, extra={"safe_fields": {k: v for k, v in fields.items() if k in SAFE_FIELDS}})


def safe_exception(exc: Exception):
    # No exception message, locals, source line or absolute user path.
    return {
        "exception_type": type(exc).__name__,
        "frames": [
            {"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(exc.__traceback__)[-12:]
        ],
    }
