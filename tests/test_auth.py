import asyncio
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from smartflow.api import create_app
from smartflow.auth import Permission
from smartflow.config import Settings
from smartflow.jobs import CreateJob, Jobs

TOKEN = "auth-fixture-desktop-token-not-secret"
SUPPORT_TOKEN = "auth-fixture-diagnostics-token-not-secret"

pytestmark = pytest.mark.integration


@pytest.fixture
def auth_client(tmp_path):
    clients = []

    def make(role="owner", mode="local_session"):
        settings = Settings(
            tmp_path / role, TOKEN, "test", auth_mode=mode, session_role=role, diagnostics_token=SUPPORT_TOKEN
        )
        client = TestClient(create_app(settings), headers={"Authorization": f"Bearer {TOKEN}"})
        client.__enter__()
        clients.append(client)
        return client

    yield make
    for client in reversed(clients):
        client.__exit__(None, None, None)


@pytest.mark.parametrize(
    "role,allowed",
    [
        (
            "owner",
            {
                "session:read",
                "schema:read",
                "jobs:read",
                "jobs:create",
                "jobs:command",
                "diagnostics:read",
                "support:export",
                "browser:manage",
                "stories:drafts:read",
                "stories:drafts:write",
            },
        ),
        (
            "operator",
            {
                "session:read",
                "schema:read",
                "jobs:read",
                "jobs:create",
                "jobs:command",
                "stories:drafts:read",
                "stories:drafts:write",
            },
        ),
        ("viewer", {"session:read", "schema:read", "jobs:read", "stories:drafts:read"}),
        ("support", {"session:read", "schema:read", "diagnostics:read", "support:export"}),
    ],
)
def test_every_api_route_enforces_role_and_token(auth_client, role, allowed):
    client = auth_client(role)
    job = Jobs(client.app.state.db).create(CreateJob(title="PRIVATE_TITLE"), "seed-job-key", "seed-trace")
    schema = client.get("/api/openapi.json").json()
    from smartflow.draft_contracts import DraftInput
    from smartflow.drafts import Drafts

    draft = Drafts(client.app.state.db).save(
        DraftInput(config={"topic": "simulation fixture"}), "seed-draft", "seed-trace"
    )
    from smartflow.assets import Assets
    from smartflow.auth import AuthMode
    from smartflow.browser_bridge import COMPAT, Bridge, PairRequest

    png = b"\x89PNG\r\n\x1a\n" + bytes(40)

    async def stream():
        yield png

    asset = asyncio.run(
        Assets(client.app.state.db).import_file(
            draft["id"], "mainImage", "image.png", len(png), "matrix-asset", stream(), "trace"
        )
    )
    pair = Bridge(client.app.state.db, AuthMode.LOCAL_SESSION).create(
        PairRequest(extension_id=COMPAT["extension_id"]), "trace"
    )
    from smartflow.story_contracts import StoryStart
    from smartflow.story_workflow import StoryWorkflow

    story = StoryWorkflow(client.app.state.db).create(
        StoryStart(draft_id=draft["id"], expected_revision=1, mode="simulation"), "matrix-story", "trace"
    )
    for route, operations in schema["paths"].items():
        selected_job = story if "/stories/" in route else job
        path = (
            route.replace("{job_id}", selected_job["id"])
            .replace("{action}", "cancel")
            .replace("{table}", "jobs")
        )
        path = (
            path.replace("{draft_id}", draft["id"])
            .replace("{asset_id}", asset["id"])
            .replace("{pair_id}", pair["id"])
        )
        for method, operation in operations.items():
            permission = operation["x-required-permission"]
            assert permission in set(Permission)
            payload = {"title": "created through API"} if method == "post" and path == "/api/jobs" else None
            if method == "post" and path == "/api/story-drafts":
                payload = {}
            elif method == "patch":
                payload = {"expected_revision": 1}
            if method == "post" and path == "/api/browser/pairings":
                payload = {"extension_id": COMPAT["extension_id"]}
            if method == "post" and path == "/api/stories":
                payload = {"draft_id": draft["id"], "expected_revision": 1, "mode": "simulation"}
                # Use the seeded command to exercise HTTP idempotency even after the draft PATCH.
            request_options = {"json": payload}
            good_headers = {
                "Idempotency-Key": "matrix-story" if path == "/api/stories" else f"matrix-{method}-created"
            }
            if method == "post" and path.endswith("/assets"):
                path += "?field=mainImage"
                request_options = {"content": png}
                good_headers |= {
                    "X-File-Name": "image.png",
                    "X-File-Size": str(len(png)),
                    "Content-Type": "application/octet-stream",
                }
            for bad_auth in ("", "Bearer wrong-session", "Basic invalid"):
                denied = client.request(
                    method, path, **request_options, headers={**good_headers, "Authorization": bad_auth}
                )
                assert denied.status_code == 401, (role, method, path)
                assert denied.headers["www-authenticate"] == "Bearer"
                assert denied.json()["error"]["code"] == "UNAUTHORIZED"
            response = client.request(method, path, **request_options, headers=good_headers)
            if permission in allowed:
                assert response.status_code in {200, 201}, (role, method, path, response.text)
            else:
                assert response.status_code == 403, (role, method, path)
                assert response.json()["error"]["code"] == "PERMISSION_DENIED"
                assert response.json()["error"]["trace_id"] == response.headers["x-trace-id"]


@pytest.mark.parametrize("mode", ["local_session", "dev_bypass"])
def test_viewer_cannot_write_or_escalate_even_during_dev_bypass(auth_client, mode):
    client = auth_client("viewer", mode)
    jobs = Jobs(client.app.state.db)
    job = jobs.create(CreateJob(title="unchanged"), "viewer-job", "viewer-trace")
    headers = {
        "X-Role": "owner",
        "X-Permissions": "jobs:create jobs:command",
        "Idempotency-Key": "blocked-create",
    }
    assert client.post("/api/jobs?role=owner", json={"title": "blocked"}, headers=headers).status_code == 403
    for action in ("cancel", "resume", "reconcile"):
        response = client.post(f"/api/jobs/{job['id']}/commands/{action}?bypass=true", headers=headers)
        assert response.status_code == 403
    assert jobs.get(job["id"])["status"] == "queued"
    assert len(jobs.list()) == 1
    assert [event["name"] for event in jobs.events(job["id"])] == ["job.created"]
    session = client.get("/api/session").json()
    assert session["role"] == "viewer" and session["auth_mode"] == mode
    assert "jobs:create" not in session["permissions"]
    assert client.get("/api/session", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/session", headers={"Origin": "https://untrusted.example"}).status_code == 403
    logs = (client.app.state.db.path.parent / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert "auth.denied" in logs and "PERMISSION_DENIED" in logs
    assert TOKEN not in logs and SUPPORT_TOKEN not in logs


def test_support_token_is_distinct_read_only_and_exports_safe_data(auth_client):
    client = auth_client()
    created = client.post(
        "/api/jobs", json={"title": "PRIVATE_TITLE"}, headers={"Idempotency-Key": "support-job"}
    ).json()
    client.headers["Authorization"] = f"Bearer {SUPPORT_TOKEN}"
    session = client.get("/api/session").json()
    assert session["actor_id"] == "diagnostics-session" and session["role"] == "support"
    assert client.get("/api/jobs").status_code == 403
    assert client.get(f"/api/jobs/{created['id']}").status_code == 403
    assert client.post(f"/api/jobs/{created['id']}/commands/cancel").status_code == 403
    rows = client.get("/api/diagnostics/database/jobs")
    assert rows.status_code == 200 and "PRIVATE_TITLE" not in rows.text
    response = client.get(f"/api/jobs/{created['id']}/support-bundle")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        content = archive.read("diagnostics.json").decode()
    assert "PRIVATE_TITLE" not in content and TOKEN not in content and SUPPORT_TOKEN not in content
    assert TOKEN not in json.dumps(session) and SUPPORT_TOKEN not in json.dumps(session)


def test_missing_policy_fails_closed_before_handler(auth_client, monkeypatch):
    reached = []

    def unclassified(*args):
        reached.append(True)
        return {"private": "must not escape"}

    monkeypatch.setattr("smartflow.api.policy", lambda permission: {})
    monkeypatch.setattr("smartflow.api.overview", unclassified)
    client = auth_client()
    response = client.get("/api/health")
    assert response.status_code == 403 and not reached
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_new_api_outside_secured_router_is_not_accidentally_public(auth_client):
    client = auth_client()
    reached = []

    def unclassified():
        reached.append(True)
        return {"private": "must not escape"}

    client.app.add_api_route("/api/unclassified", unclassified)
    assert client.get("/api/unclassified", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/unclassified").status_code == 403
    assert not reached
    assert client.get("/", headers={"Authorization": ""}).status_code == 200


@pytest.mark.parametrize("mode,frozen", [("prod", False), ("dev", True), ("test", True)])
def test_dev_bypass_cannot_start_in_prod_or_packaged_app(tmp_path, monkeypatch, mode, frozen):
    import sys

    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    directory = tmp_path / "not-created"
    with pytest.raises(ValueError, match="forbidden"):
        create_app(Settings(directory, TOKEN, mode, auth_mode="dev_bypass"))
    assert not directory.exists()


@pytest.mark.parametrize(
    "config",
    [
        {"auth_mode": "unknown"},
        {"session_role": "superadmin"},
        {"token": ""},
        {"diagnostics_token": "short"},
        {"diagnostics_token": TOKEN},
    ],
)
def test_invalid_auth_config_fails_before_database_creation(tmp_path, config):
    values = {"token": TOKEN, **config}
    directory = tmp_path / "not-created"
    with pytest.raises(ValueError):
        create_app(Settings(directory, **values))
    assert not directory.exists()


def test_settings_repr_does_not_expose_credentials(tmp_path):
    settings = Settings(tmp_path, TOKEN, diagnostics_token=SUPPORT_TOKEN)
    assert TOKEN not in repr(settings) and SUPPORT_TOKEN not in repr(settings)
