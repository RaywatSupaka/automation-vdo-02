import io
import json
import zipfile
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from smartflow.contracts import (
    DatabaseResponse,
    DiagnosticResponse,
    ErrorResponse,
    EventResponse,
    EventRow,
    HealthResponse,
    JobResponse,
    JobRow,
    LogResponse,
    ReceiptRow,
    SessionResponse,
)
from smartflow.diagnostics import support_bundle
from smartflow.engine import Engine
from smartflow.jobs import Jobs
from smartflow.observability import emit
from smartflow.providers import Simulator

pytestmark = pytest.mark.integration


def test_create_list_trace_and_idempotency(client):
    payload = {"title": "API work", "scenario": "success"}
    response = client.post("/api/jobs", json=payload, headers={"Idempotency-Key": "api-test-command"})
    assert response.status_code == 201
    job = response.json()
    assert job["trace_id"] == response.headers["x-trace-id"]
    repeat = client.post("/api/jobs", json=payload, headers={"Idempotency-Key": "api-test-command"})
    assert repeat.json()["id"] == job["id"]
    assert len(client.get("/api/jobs").json()) == 1
    assert client.get(f"/api/jobs/{job['id']}/events").json()[0]["name"] == "job.created"


def test_health_reports_release_version(client):
    assert client.get("/api/health").json()["version"] == "0.2.0"


def test_failure_scenarios_are_allowed_in_test_mode(client):
    for scenario in ("auth_required", "unknown_send", "save_failure", "transient", "pending"):
        response = client.post(
            "/api/jobs",
            json={"title": "Simulation", "scenario": scenario},
            headers={"Idempotency-Key": f"test-{scenario}"},
        )
        assert response.status_code == 201
        assert response.json()["scenario"] == scenario


def test_failure_scenarios_are_denied_in_prod_mode(tmp_path):
    from fastapi.testclient import TestClient
    from smartflow.api import create_app
    from smartflow.config import Settings

    token = "prod-simulation-test-token"
    app = create_app(Settings(tmp_path, token, "prod"))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as prod:
        for scenario in ("auth_required", "unknown_send", "save_failure", "transient", "pending"):
            response = prod.post(
                "/api/jobs",
                json={"title": "Simulation", "scenario": scenario},
                headers={"Idempotency-Key": f"prod-{scenario}"},
            )
            assert response.status_code == 409
            assert response.json()["error"]["code"] == "SCENARIO_NOT_ALLOWED"
        success = prod.post(
            "/api/jobs",
            json={"title": "Allowed", "scenario": "success"},
            headers={"Idempotency-Key": "prod-success"},
        )
        assert success.status_code == 201
        assert len(prod.get("/api/jobs").json()) == 1


def test_auth_origin_and_schema_are_protected(client):
    for path in ["/api/jobs", "/api/openapi.json", "/api/diagnostics/database", "/api/diagnostics/logs"]:
        assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get(path, headers={"Origin": "https://untrusted.example"}).status_code == 403
    schema = client.get("/api/openapi.json").json()
    assert "HTTPBearer" in schema["components"]["securitySchemes"]


def test_validation_does_not_echo_private_input(client):
    response = client.post(
        "/api/jobs",
        json={"title": "PRIVATE_TITLE", "scenario": "PRIVATE_SECRET"},
        headers={"Idempotency-Key": "api-invalid"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INPUT_INVALID"
    assert "PRIVATE" not in response.text


def test_diagnostics_are_allowlisted_and_no_arbitrary_sql(client):
    response = client.post(
        "/api/jobs", json={"title": "PRIVATE_TITLE"}, headers={"Idempotency-Key": "api-support"}
    )
    job_id = response.json()["id"]
    assert client.get("/api/diagnostics/database").status_code == 200
    assert "PRIVATE_TITLE" not in client.get("/api/diagnostics/database/jobs").text
    assert client.get("/api/diagnostics/database/sqlite_master").status_code == 422
    bundle = client.get(f"/api/jobs/{job_id}/support-bundle")
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        content = archive.read("diagnostics.json").decode()
    assert "PRIVATE_TITLE" not in content
    assert job_id in content


def test_not_found_has_error_code_and_trace(client):
    response = client.get("/api/jobs/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
    assert response.json()["error"]["trace_id"] == response.headers["x-trace-id"]


def test_runtime_log_excludes_unapproved_fields(system):
    db, jobs, engine, clock, create = system
    emit(db.logger, "test.safe", trace_id="test-trace", prompt="SECRET", token="SECRET", title="SECRET")
    text = (engine.data_dir / "logs" / "runtime.jsonl").read_text(encoding="utf-8")
    assert "SECRET" not in text
    assert json.loads(text.splitlines()[-1])["trace_id"] == "test-trace"


def test_support_preserves_reason_and_omits_result(system):
    db, jobs, engine, clock, create = system
    job = create("unknown_send", title="PRIVATE_TITLE")
    engine.tick()
    with zipfile.ZipFile(io.BytesIO(support_bundle(db, job["id"]))) as archive:
        report = archive.read("diagnostics.json").decode()
    assert "SEND_ACCEPTANCE_UNKNOWN" in report
    assert "PRIVATE_TITLE" not in report
    assert "SMARTFLOW SIMULATION CHECKPOINT" not in report


def test_all_json_response_contracts_and_saved_openapi(client):
    created = client.post("/api/jobs", json={"title": "private"}, headers={"Idempotency-Key": "contract-job"})
    job = JobResponse.model_validate(created.json())
    db = client.app.state.db
    Engine(db, Simulator(db), db.path.parent).tick()
    routes = {
        "/api/session": SessionResponse,
        "/api/health": HealthResponse,
        "/api/jobs": list[JobResponse],
        f"/api/jobs/{job.id}": JobResponse,
        f"/api/jobs/{job.id}/events": list[EventResponse],
        f"/api/jobs/{job.id}/diagnostics": DiagnosticResponse,
        "/api/diagnostics/database": DatabaseResponse,
        "/api/diagnostics/database/jobs": list[JobRow],
        "/api/diagnostics/database/receipts": list[ReceiptRow],
        "/api/diagnostics/database/events": list[EventRow],
        "/api/diagnostics/logs": list[LogResponse],
    }
    for path, model in routes.items():
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
        TypeAdapter(model).validate_python(response.json())
    schema = client.get("/api/openapi.json").json()
    saved = Path(__file__).resolve().parents[1] / "contracts/openapi.json"
    assert schema == json.loads(saved.read_text(encoding="utf-8"))
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            assert operation["security"] == [{"HTTPBearer": []}]
            responses = operation["responses"]
            for status, response in responses.items():
                for content in response.get("content", {}).values():
                    assert content["schema"], (path, status)
            for status in ("401", "403", "422", "500"):
                assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith(
                    "/ErrorResponse"
                )
    archive = schema["paths"]["/api/jobs/{job_id}/support-bundle"]["get"]["responses"]["200"]
    assert set(archive["content"]) == {"application/zip"}


@pytest.mark.parametrize(
    "method,path,status,code",
    [
        ("GET", "/api/missing", 404, "ROUTE_NOT_FOUND"),
        ("POST", "/api/health", 405, "METHOD_NOT_ALLOWED"),
        ("GET", "/api/jobs/missing", 404, "JOB_NOT_FOUND"),
        ("GET", "/api/jobs?limit=0", 422, "INPUT_INVALID"),
    ],
)
def test_error_status_matches_envelope(client, method, path, status, code):
    response = client.request(method, path)
    error = ErrorResponse.model_validate(response.json()).error
    assert response.status_code == error.http_status == status
    assert error.code == code
    assert error.trace_id == response.headers["x-trace-id"]
    if status == 405:
        assert "GET" in response.headers["allow"]


def test_unexpected_exception_is_safe_and_traceable(client, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("PRIVATE_SECRET C:/private/customer/file")

    monkeypatch.setattr(Jobs, "list", broken)
    response = client.get("/api/jobs")
    assert response.status_code == 500
    error = ErrorResponse.model_validate(response.json()).error
    assert error.code == "INTERNAL_ERROR" and error.http_status == 500
    logs = client.get("/api/diagnostics/logs").json()
    failure = next(row for row in logs if row["event"] == "api.exception")
    assert failure["trace_id"] == error.trace_id == response.headers["x-trace-id"]
    assert failure["exception_type"] == "RuntimeError" and failure["frames"]
    assert "PRIVATE_SECRET" not in json.dumps(logs) + response.text
    assert "C:/private" not in json.dumps(logs)


def test_validation_extra_key_does_not_leak_user_content(client):
    response = client.post(
        "/api/jobs",
        json={"title": "PRIVATE_TITLE", "PRIVATE_KEY": "PRIVATE_VALUE"},
        headers={"Idempotency-Key": "private-fields"},
    )
    assert response.status_code == 422
    assert "PRIVATE" not in response.text
    assert response.json()["fields"] == [{"field": "body.unknown", "type": "extra_forbidden"}]


def test_pagination_ties_and_event_cursor(client):
    from smartflow.models import Job

    ids = []
    for index in range(3):
        response = client.post(
            "/api/jobs", json={"title": "page"}, headers={"Idempotency-Key": f"pagination-{index}"}
        )
        ids.append(response.json()["id"])
    with client.app.state.db.transaction(write=True) as session:
        for job_id in ids:
            session.get(Job, job_id).created_at = 1000
    expected = sorted(ids, reverse=True)
    for route in ("/api/jobs", "/api/diagnostics/database/jobs"):
        actual = [client.get(f"{route}?limit=1&offset={i}").json()[0]["id"] for i in range(3)]
        assert actual == expected
        assert client.get(f"{route}?offset=3").json() == []
        assert client.get(f"{route}?offset=-1").status_code == 422
    job_id = ids[0]
    client.post(f"/api/jobs/{job_id}/commands/cancel")
    first = client.get(f"/api/jobs/{job_id}/events?limit=1").json()[0]
    second = client.get(f"/api/jobs/{job_id}/events?after={first['id']}&limit=1").json()[0]
    assert second["id"] > first["id"] and second["name"] == "job.cancel"
    assert client.get(f"/api/jobs/{job_id}/events?after={second['id']}").json() == []


def test_command_trace_survives_duplicate_commands_and_reconciliation(client):
    created = client.post(
        "/api/jobs",
        json={"title": "private", "scenario": "unknown_send"},
        headers={"Idempotency-Key": "trace-scenario"},
    )
    job = created.json()
    db = client.app.state.db
    engine = Engine(db, Simulator(db), db.path.parent)
    engine.tick()
    blocked = client.post(f"/api/jobs/{job['id']}/commands/resume")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "SEND_ACCEPTANCE_UNKNOWN"
    assert blocked.json()["error"]["stage"] == "generate"
    trace_ids = []
    for action in ("cancel", "cancel", "reconcile", "reconcile", "resume", "resume"):
        response = client.post(f"/api/jobs/{job['id']}/commands/{action}")
        assert response.status_code == 200, response.text
        assert response.json()["trace_id"] == job["trace_id"]
        trace_ids.append(response.headers["x-trace-id"])
    events = client.get(f"/api/jobs/{job['id']}/events").json()
    commands = [event for event in events if event["details"].get("command_trace_id")]
    assert [event["details"]["command_trace_id"] for event in commands] == trace_ids
    assert all(event["trace_id"] == job["trace_id"] for event in events)
    assert sum(event["details"].get("outcome") == "noop" for event in commands) == 2
    engine.tick()
    from smartflow.models import SimulatedRequest
    from sqlalchemy import select

    with db.transaction() as session:
        assert session.scalar(select(SimulatedRequest.sends)) == 1
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "completed"
    log = client.get("/api/diagnostics/logs?limit=200").json()
    blocked_trace = blocked.headers["x-trace-id"]
    assert any(
        row.get("command_trace_id") == blocked_trace and row.get("trace_id") == job["trace_id"] for row in log
    )
    assert any(
        row.get("trace_id") == blocked_trace and row.get("code") == "SEND_ACCEPTANCE_UNKNOWN" for row in log
    )


def test_idempotency_conflict_has_consistent_contract(client):
    headers = {"Idempotency-Key": "conflict-scenario"}
    client.post("/api/jobs", json={"title": "one"}, headers=headers)
    response = client.post("/api/jobs", json={"title": "two"}, headers=headers)
    error = ErrorResponse.model_validate(response.json()).error
    assert response.status_code == error.http_status == 409
    assert error.code == "IDEMPOTENCY_CONFLICT"
    assert len(client.get("/api/jobs").json()) == 1
