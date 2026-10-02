"""Exercise the actual portable EXE with isolated data; no real providers."""

import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def wait_for(predicate, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (httpx.TransportError, sqlite3.OperationalError):
            pass
        time.sleep(0.15)
    raise RuntimeError("Packaged smoke condition timed out")


def main():
    executable = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist/SmartFlow Next/SmartFlow Next.exe"
    directory = Path(tempfile.mkdtemp(prefix="smartflow-package-ทดสอบ-"))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    token = secrets.token_urlsafe(32)
    env = {
        **os.environ,
        "SMARTFLOW_DATA_DIR": str(directory),
        "SMARTFLOW_PORT": str(port),
        "SMARTFLOW_MODE": "prod",
        "SMARTFLOW_API_TOKEN": token,
        "SMARTFLOW_AUTH_MODE": "local_session",
        "SMARTFLOW_SESSION_ROLE": "owner",
        "SMARTFLOW_DIAGNOSTICS_TOKEN": "",
    }
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{port}", headers={"Authorization": f"Bearer {token}"}, timeout=2
    )

    def launch(command):
        return subprocess.Popen(
            [str(executable.resolve()), *command],
            env=env,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )

    def stop(process):
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        time.sleep(0.6)  # The child detects parent death using its process handle.

    def state(job_id):
        response = client.get(f"/api/jobs/{job_id}")
        response.raise_for_status()
        return response.json()["status"]

    report = {
        "compiled_ui": False,
        "api_worker": False,
        "restart_no_resend": False,
        "automatic_save_recovery": False,
        "native_webview": False,
        "clean_machine": False,
    }
    process = launch(["serve", "--port", str(port)])
    try:
        wait_for(lambda: client.get("/api/health").json().get("worker_alive"))
        assert 'id="root"' in client.get("/").text
        report["compiled_ui"] = report["api_worker"] = True
        response = client.post(
            "/api/jobs",
            json={"title": "Packaged crash test", "scenario": "unknown_send"},
            headers={"Idempotency-Key": "package-unknown-test"},
        )
        response.raise_for_status()
        job_id = response.json()["id"]
        wait_for(lambda: state(job_id) == "needs_review")
        stop(process)
        process = launch(["serve", "--port", str(port)])
        wait_for(lambda: client.get("/api/health").json().get("worker_alive"))
        assert state(job_id) == "needs_review"
        client.post(f"/api/jobs/{job_id}/commands/reconcile").raise_for_status()
        wait_for(lambda: state(job_id) == "completed")
        with sqlite3.connect((directory / "smartflow.db").as_uri() + "?mode=ro", uri=True) as connection:
            assert connection.execute("SELECT sum(sends) FROM simulated_requests").fetchone()[0] == 1
        report["restart_no_resend"] = True
        response = client.post(
            "/api/jobs",
            json={"title": "Packaged save recovery", "scenario": "save_failure"},
            headers={"Idempotency-Key": "package-save-test"},
        )
        response.raise_for_status()
        wait_for(lambda: state(response.json()["id"]) == "completed")
        report["automatic_save_recovery"] = True
    finally:
        stop(process)
        client.close()
    process = launch(["desktop", "--desktop-smoke", "--port", str(port)])
    try:
        process.wait(timeout=40)
        marker = directory / "desktop-smoke.json"
        assert process.returncode == 0 and marker.exists(), "Native WebView did not render the dashboard"
        report["native_webview"] = json.loads(marker.read_text())["dashboard_rendered"]
    finally:
        stop(process)
    target = ROOT / "build" / "packaged-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
