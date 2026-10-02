import io
import json
import zipfile

import pytest
from smartflow.diagnostics import support_bundle
from smartflow.observability import emit

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
