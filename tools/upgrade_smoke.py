"""Prove an isolated 0.1.0 portable database upgrades safely to 0.2.0."""

import json
import secrets
import sqlite3
import tempfile
from pathlib import Path

from packaged_smoke import client_for, free_port, job_state, launch, ready, stop, wait_for

ROOT = Path(__file__).resolve().parents[1]


def schema_version(database):
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def main():
    old = ROOT / "build" / "previous-package" / "SmartFlow Next 0.1.0" / "SmartFlow Next.exe"
    current = ROOT / "dist" / "SmartFlow Next" / "SmartFlow Next.exe"
    assert old.exists() and current.exists(), "Both portable executables are required"
    directory = Path(tempfile.mkdtemp(prefix="smartflow-upgrade-ทดสอบ-"))
    token, port = secrets.token_urlsafe(32), free_port()
    database = directory / "smartflow.db"
    old_job_id = None
    old_client = client_for(port, token)
    old_process = launch(old, directory, "prod", port, token)
    try:
        old_health = wait_for(lambda: old_client.get("/api/health").json())
        assert old_health["version"] == "0.1.0"
        response = old_client.post(
            "/api/jobs",
            json={"title": "Upgrade fixture", "scenario": "success"},
            headers={"Idempotency-Key": "upgrade-old-success"},
        )
        if response.status_code == 201:
            old_job_id = response.json()["id"]
            wait_for(lambda: job_state(old_client, old_job_id) == "completed")
        else:
            assert response.status_code in {401, 403, 404, 422}, response.text
    finally:
        stop(old_process)
        old_client.close()

    assert schema_version(database) == "0001"
    new_port = free_port()
    new_client = client_for(new_port, token)
    new_process = launch(current, directory, "prod", new_port, token)
    try:
        health = wait_for(lambda: ready(new_client))
        assert health["version"] == "0.2.0" and health["worker_state"] == "ready"
        assert schema_version(database) == "0004"
        backups = list((directory / "backups").glob("before-0001-*.sqlite3"))
        assert len(backups) == 1, "Expected exactly one pre-upgrade backup"
        with sqlite3.connect(backups[0].as_uri() + "?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001"
        if old_job_id:
            assert job_state(new_client, old_job_id) == "completed"
        report = {
            "old_version": "0.1.0",
            "old_schema": "0001",
            "old_job_created": bool(old_job_id),
            "new_version": "0.2.0",
            "new_schema": "0004",
            "backup_integrity": True,
            "old_job_preserved": bool(old_job_id),
            "worker_ready": True,
        }
    finally:
        stop(new_process)
        new_client.close()
    target = ROOT / "build" / "upgrade-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
