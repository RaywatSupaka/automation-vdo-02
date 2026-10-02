"""Read-only diagnostics that also work when the API cannot start."""

import json
import sqlite3
from collections import deque

from smartflow import __version__


def diagnose(settings):
    report = {"version": __version__, "mode": settings.mode, "database": "missing", "logs": []}
    if settings.db_path.exists():
        try:
            with sqlite3.connect(settings.db_path.as_uri() + "?mode=ro", uri=True, timeout=2) as connection:
                connection.execute("PRAGMA query_only=ON")
                check = connection.execute("PRAGMA quick_check").fetchone()[0]
                report["database"] = "ok" if check == "ok" else "integrity_error"
                report["schema_revision"] = connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()[0]
                report["job_counts"] = dict(
                    connection.execute("SELECT status, count(*) FROM jobs GROUP BY status")
                )
        except sqlite3.Error as exc:
            report["database"] = "unreadable"
            report["exception_type"] = type(exc).__name__
    for name in ("runtime.jsonl", "worker.jsonl"):
        path = settings.data_dir / "logs" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in deque(handle, maxlen=30):
                try:
                    report["logs"].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return report
