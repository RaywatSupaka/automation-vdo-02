"""Exercise the actual portable EXE with isolated data; no real providers."""

import hashlib
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
from uuid import uuid4

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


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def launch(executable, directory, mode, port, token, command="serve"):
    directory.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "SMARTFLOW_DATA_DIR": str(directory),
        "SMARTFLOW_PORT": str(port),
        "SMARTFLOW_MODE": mode,
        "SMARTFLOW_API_TOKEN": token,
        "SMARTFLOW_AUTH_MODE": "local_session",
        "SMARTFLOW_SESSION_ROLE": "owner",
        "SMARTFLOW_DIAGNOSTICS_TOKEN": "",
    }
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    arguments = [str(executable.resolve()), command, "--port", str(port)]
    if command == "desktop":
        arguments.insert(2, "--desktop-smoke")
    return subprocess.Popen(
        arguments,
        env=env,
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def stop(process):
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
            )
        else:
            process.terminate()
        process.wait(timeout=10)


def client_for(port, token):
    return httpx.Client(
        base_url=f"http://127.0.0.1:{port}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=2,
        trust_env=False,
    )


def ready(client):
    response = client.get("/api/health")
    if response.status_code != 200:
        return False
    health = response.json()
    return health if health.get("version") == "0.2.0" and health.get("worker_state") == "ready" else False


def job_state(client, job_id):
    response = client.get(f"/api/jobs/{job_id}")
    response.raise_for_status()
    return response.json()["status"]


def prod_smoke(executable, directory, report):
    port, token = free_port(), secrets.token_urlsafe(32)
    client = client_for(port, token)
    process = launch(executable, directory, "prod", port, token)
    try:
        health = wait_for(lambda: ready(client))
        assert health["version"] == "0.2.0" and health["worker_state"] == "ready"
        report["version"] = report["worker_ready"] = True
        assert 'id="root"' in client.get("/").text
        report["compiled_ui"] = report["api_worker"] = True

        success = client.post(
            "/api/jobs",
            json={"title": "Packaged success", "scenario": "success"},
            headers={"Idempotency-Key": "package-prod-success"},
        )
        success.raise_for_status()
        wait_for(lambda: job_state(client, success.json()["id"]) == "completed")
        denied = client.post(
            "/api/jobs",
            json={"title": "Denied simulator fault", "scenario": "unknown_send"},
            headers={"Idempotency-Key": "package-prod-denied"},
        )
        assert denied.status_code == 409 and denied.json()["error"]["code"] == "SCENARIO_NOT_ALLOWED"
        report["prod_fault_scenarios_denied"] = True

        created = client.post(
            "/api/story-drafts",
            json={"config": {"topic": "PRIVATE DRAFT BEFORE RESTART"}},
            headers={"Idempotency-Key": "package-draft-create"},
        )
        created.raise_for_status()
        draft_id = created.json()["id"]
        updated = client.patch(
            f"/api/story-drafts/{draft_id}",
            json={"expected_revision": created.json()["revision"], "config": {"topic": "PRIVATE STORY"}},
            headers={"Idempotency-Key": "package-draft-update"},
        )
        updated.raise_for_status()
        revision = updated.json()["revision"]
        stop(process)
        process = launch(executable, directory, "prod", port, token)
        wait_for(lambda: ready(client))
        restored = client.get(f"/api/story-drafts/{draft_id}")
        restored.raise_for_status()
        assert restored.json()["revision"] == revision
        assert restored.json()["config"]["topic"] == "PRIVATE STORY"
        report["draft_restore"] = True

        started = client.post(
            "/api/stories",
            json={"draft_id": draft_id, "expected_revision": revision, "mode": "simulation"},
            headers={"Idempotency-Key": "package-story-create"},
        )
        assert started.status_code == 201, started.text
        story_id = started.json()["id"]
        bridge = client.get("/api/browser")
        bridge.raise_for_status()
        info = bridge.json()
        pairing = client.post("/api/browser/pairings", json={"extension_id": info["extension_id"]})
        pairing.raise_for_status()
        agent_token = secrets.token_urlsafe(48)
        paired = client.post(
            "/api/browser/pair",
            headers={"Authorization": f"Bearer {pairing.json()['code']}"},
            json={
                "extension_id": info["extension_id"],
                "agent_token": agent_token,
                "extension_version": info["extension_version"],
                "helper_version": info["helper_version"],
            },
        )
        paired.raise_for_status()
        agent_headers = {"Authorization": f"Bearer {agent_token}"}
        connection_id = str(uuid4())
        common = {
            "connection_id": connection_id,
            "extension_version": info["extension_version"],
            "helper_version": info["helper_version"],
            "capability": "story_simulator_v1",
        }

        def sync():
            response = client.post(
                "/api/browser/work", json={"action": "sync", **common}, headers=agent_headers
            )
            response.raise_for_status()
            return response.json()["task"]

        task = wait_for(sync)
        command = {
            "connection_id": connection_id,
            "operation_id": task["operation_id"],
            "request_id": task["request_id"],
            "lease_epoch": task["lease_epoch"],
        }
        grant = client.post("/api/browser/work", json={"action": "grant", **command}, headers=agent_headers)
        grant.raise_for_status()
        assert grant.json()["granted"] is True
        result_text = "[SIMULATION ONLY]\n" + task["topic"]
        result = client.post(
            "/api/browser/work",
            json={"action": "result", **command, "result": result_text},
            headers=agent_headers,
        )
        result.raise_for_status()
        assert result.json()["persisted"] is True
        wait_for(lambda: client.get(f"/api/stories/{story_id}").json()["status"] == "completed")
        detail = client.get(f"/api/stories/{story_id}").json()
        artifact = directory / "story-artifacts" / f"{task['operation_id']}.txt"
        assert artifact.read_text(encoding="utf-8") == result_text
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == detail["sha256"]
        diagnostic = client.get(f"/api/diagnostics/stories/{story_id}")
        diagnostic.raise_for_status()
        assert "PRIVATE STORY" not in diagnostic.text
        report["story_simulation"] = True
    finally:
        stop(process)
        client.close()


def test_fault_smoke(executable, directory, report):
    port, token = free_port(), secrets.token_urlsafe(32)
    client = client_for(port, token)
    process = launch(executable, directory, "test", port, token)
    try:
        wait_for(lambda: ready(client))
        response = client.post(
            "/api/jobs",
            json={"title": "Packaged crash test", "scenario": "unknown_send"},
            headers={"Idempotency-Key": "package-unknown-test"},
        )
        response.raise_for_status()
        job_id = response.json()["id"]
        wait_for(lambda: job_state(client, job_id) == "needs_review")
        stop(process)
        process = launch(executable, directory, "test", port, token)
        wait_for(lambda: ready(client))
        assert job_state(client, job_id) == "needs_review"
        client.post(f"/api/jobs/{job_id}/commands/reconcile").raise_for_status()
        wait_for(lambda: job_state(client, job_id) == "completed")
        with sqlite3.connect((directory / "smartflow.db").as_uri() + "?mode=ro", uri=True) as connection:
            assert connection.execute("SELECT sum(sends) FROM simulated_requests").fetchone()[0] == 1
        report["restart_no_resend"] = True
        response = client.post(
            "/api/jobs",
            json={"title": "Packaged save recovery", "scenario": "save_failure"},
            headers={"Idempotency-Key": "package-save-test"},
        )
        response.raise_for_status()
        wait_for(lambda: job_state(client, response.json()["id"]) == "completed")
        report["automatic_save_recovery"] = True
    finally:
        stop(process)
        client.close()


def desktop_smoke(executable, directory, report):
    port, token = free_port(), secrets.token_urlsafe(32)
    process = launch(executable, directory, "prod", port, token, "desktop")
    try:
        process.wait(timeout=40)
        marker = directory / "desktop-smoke.json"
        assert process.returncode == 0 and marker.exists(), "Native WebView did not render the dashboard"
        report["native_webview"] = json.loads(marker.read_text(encoding="utf-8"))["dashboard_rendered"]
    finally:
        stop(process)


def main():
    executable = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist/SmartFlow Next/SmartFlow Next.exe"
    directory = Path(tempfile.mkdtemp(prefix="smartflow-package-ทดสอบ-"))
    report = {
        "version": False,
        "worker_ready": False,
        "compiled_ui": False,
        "api_worker": False,
        "prod_fault_scenarios_denied": False,
        "draft_restore": False,
        "story_simulation": False,
        "restart_no_resend": False,
        "automatic_save_recovery": False,
        "native_webview": False,
        "clean_machine": False,
    }
    prod_smoke(executable, directory / "prod", report)
    test_fault_smoke(executable, directory / "test", report)
    desktop_smoke(executable, directory / "desktop", report)
    target = ROOT / "build" / "packaged-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
