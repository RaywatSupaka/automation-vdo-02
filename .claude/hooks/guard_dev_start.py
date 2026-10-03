"""PreToolUse guard: block starting Dev on real data while a migration is uncommitted.

migrate() upgrades to the Alembic head at every desktop/API start, so an uncommitted file in
migrations/versions/ is applied to .smartflow/ immediately. See docs/development/parallel-work.md.
Allowed when the command sets SMARTFLOW_DATA_DIR (sandbox) or SMARTFLOW_ALLOW_PENDING_MIGRATION=1.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
VERSIONS = "backend/smartflow/migrations/versions"
# Only launches count; mentioning a launcher file (git diff, ruff, cat) does not.
START = re.compile(
    (
        r"(wscript|cscript)(\.exe)?\s+P*RUN_DEV\.vbs"
        r"|(^|[;&|(]|\bstart\s+(\"\"\s+)?|\bcmd(\.exe)?\s+/c\s+)\s*P*RUN_DEV\.(bat|vbs)"
        r"|pythonw?(\.exe)?[\"']?\s+P*desktop_entry\.py"
        r"|pythonw?(\.exe)?[\"']?\s+P*smartflow[./\\]cli(\.py)?\s+(desktop|serve|api)\b"
        r"|-m\s+smartflow(\.cli)?\s+(desktop|serve|api)\b"
    ).replace("P*", r"[\"']?[^\s\"';&|]*"),
    re.IGNORECASE,
)
SANDBOX = re.compile(r"SMARTFLOW_DATA_DIR\s*=|SMARTFLOW_ALLOW_PENDING_MIGRATION\s*=\s*['\"]?1")


def pending():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", VERSIONS],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode:
        return None
    return [line[3:] for line in result.stdout.splitlines() if line[3:].endswith(".py")]


def main():
    payload = json.load(sys.stdin)
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not START.search(command) or SANDBOX.search(command):
        return 0
    files = pending()
    if files is None:
        print(json.dumps({"systemMessage": "guard_dev_start: git status failed; migration check skipped"}))
        return 0
    if not files:
        return 0
    reason = (
        "Blocked: uncommitted migration(s) " + ", ".join(files) + " would be applied to real Dev data "
        "(.smartflow/) and cannot be downgraded. Set SMARTFLOW_DATA_DIR to a sandbox, commit the "
        "migration first, or, with the owner's explicit approval, prefix SMARTFLOW_ALLOW_PENDING_MIGRATION=1. "
        "See docs/development/parallel-work.md."
    )
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
