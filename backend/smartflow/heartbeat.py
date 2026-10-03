"""Worker signals kept separate: alive (process exists), ready (loop beat recently), stalled.

The worker loop writes a small heartbeat file; the host compares it with wall time because the
two processes share no monotonic clock. A stale beat means the loop made no progress.
"""

import json
import os
from pathlib import Path

READY_SECONDS = 5.0
STALL_SECONDS = 30.0


def heartbeat_path(data_dir):
    return Path(data_dir) / "worker.heartbeat"


def beat(data_dir, pid, now):
    target = heartbeat_path(data_dir)
    temporary = target.with_name(f"{target.name}.{pid}.part")
    temporary.write_text(json.dumps({"pid": pid, "at": now}), encoding="utf-8")
    os.replace(temporary, target)


def read(data_dir):
    try:
        data = json.loads(heartbeat_path(data_dir).read_text(encoding="utf-8"))
        return int(data["pid"]), float(data["at"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def worker_state(alive, pid, heartbeat, now, started_at):
    """Return (state, heartbeat_age). Only a beat from the current process counts."""
    if not alive:
        return "down", None
    if not heartbeat or heartbeat[0] != pid:
        return ("stalled" if now - started_at >= STALL_SECONDS else "starting"), None
    age = max(0.0, now - heartbeat[1])
    if age <= READY_SECONDS:
        return "ready", age
    return ("stalled" if age >= STALL_SECONDS else "late"), age
