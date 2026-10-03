from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from smartflow.api import create_app
from smartflow.config import Settings
from smartflow.draft_contracts import REGISTRY, DraftInput, DraftUpdate
from smartflow.draft_models import DraftCommand, DraftEvent, StoryDraft
from smartflow.drafts import Drafts
from smartflow.errors import AppError
from sqlalchemy import func, select

TOKEN = "draft-fixture-token-not-production"
KEY = {"Idempotency-Key": "draft-create-key"}


def test_incomplete_draft_survives_new_api_process_and_does_not_create_job(tmp_path):
    settings = Settings(tmp_path, TOKEN, "test")
    headers = {"Authorization": f"Bearer {TOKEN}", **KEY}
    with TestClient(create_app(settings), headers=headers) as client:
        saved = client.post(
            "/api/story-drafts", json={"config": {"topic": "", "scenes": "-"}, "active_step": 2}
        )
        assert saved.status_code == 201, saved.text
        data = saved.json()
        assert len(data["config"]) == len(REGISTRY) == 95
        assert data["issues"] == [
            {"field": "scenes", "code": "VALUE_OUT_OF_RANGE"},
            {"field": "topic", "code": "FIELD_REQUIRED"},  # Reported, never blocks saving.
        ]
        assert client.get("/api/jobs").json() == []
    with TestClient(create_app(settings), headers=headers) as restarted:
        assert restarted.get(f"/api/story-drafts/{data['id']}").json() == data
        assert restarted.get("/api/story-drafts").json()[0]["active_step"] == 2


def test_duplicate_create_and_update_returns_original_ack_without_duplicate_events(client):
    payload = {"config": {"topic": "PRIVATE_STORY", "visualCustom": "hidden option kept"}}
    initial = client.post("/api/story-drafts", json=payload, headers=KEY).json()
    assert client.post("/api/story-drafts", json=payload, headers=KEY).json() == initial
    url = f"/api/story-drafts/{initial['id']}"
    update = {"expected_revision": 1, "config": {**initial["config"], "topic": "updated"}, "active_step": 3}
    updated = client.patch(url, json=update, headers={"Idempotency-Key": "update-command"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert (
        client.patch(url, json=update, headers={"Idempotency-Key": "update-command"}).json() == updated.json()
    )
    assert client.post("/api/story-drafts", json=payload, headers=KEY).json() == initial
    assert client.get(url).json()["revision"] == 2  # Old retry ACK never rolls storage back.
    assert client.get(url).json()["config"]["visualCustom"] == "hidden option kept"
    events = client.get(f"/api/diagnostics/drafts/{initial['id']}/events").json()
    assert [e["revision"] for e in events] == [1, 2]
    assert events[1]["trace_id"] == updated.headers["x-trace-id"]
    assert (
        client.get(f"/api/diagnostics/drafts/{initial['id']}/events?after={events[0]['id']}").json()
        == events[1:]
    )
    assert client.patch(url, json=update, headers={"Idempotency-Key": "different-command"}).status_code == 409
    assert (
        client.post("/api/story-drafts", json={}, headers=KEY).json()["error"]["code"]
        == "IDEMPOTENCY_CONFLICT"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"config": {"unknown_secret": "PRIVATE_INPUT"}},
        {"config": {"topic": "x" * 2001}},
        {"config": {"cta": "true"}},
        {"config": {"scenes": 10}},
        {"active_step": 5},
        {"active_step": True},
        {"schema_version": 2},
        {"owner_scope": "someone-else"},
        {"config": {"mainImage": ["C:/private/image.png"]}},
    ],
)
def test_closed_draft_schema_rejects_wrong_types_and_never_echoes_content(client, payload):
    result = client.post("/api/story-drafts", json=payload, headers=KEY)
    assert result.status_code == 422
    assert "PRIVATE_INPUT" not in result.text and "unknown_secret" not in result.text
    assert client.get("/api/story-drafts").json() == []


def test_asset_references_are_not_acknowledged_before_import_exists(client):
    result = client.post("/api/story-drafts", json={"config": {"mainImage": [str(uuid4())]}}, headers=KEY)
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "DRAFT_ASSET_INVALID"


MP3 = b"ID3" + bytes(40)


def new_draft(client):
    return client.post("/api/story-drafts", json={}, headers={"Idempotency-Key": str(uuid4())}).json()


def imported(client, draft_id, field="musicFiles"):
    result = client.post(
        f"/api/story-drafts/{draft_id}/assets?field={field}",
        content=MP3,
        headers={
            "Idempotency-Key": str(uuid4()),
            "X-File-Name": "track.mp3",
            "X-File-Size": str(len(MP3)),
            "Content-Type": "application/octet-stream",
        },
    )
    assert result.status_code == 200, result.text
    return result.json()["id"]


def patch(client, draft, key=None, **config):
    return client.patch(
        f"/api/story-drafts/{draft['id']}",
        json={"expected_revision": draft["revision"], "config": {**draft["config"], **config}},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def events(client, draft_id):
    return client.get(f"/api/diagnostics/drafts/{draft_id}/events").json()


def asset_issues(response):
    return [issue for issue in response.json()["issues"] if issue["code"].startswith("DRAFT_ASSET")]


def test_missing_asset_already_referenced_never_blocks_unrelated_edits(client):
    from smartflow.assets import asset_path

    draft = new_draft(client)
    asset = imported(client, draft["id"])
    saved = patch(client, draft, musicFiles=[asset])
    assert saved.status_code == 200, saved.text
    assert asset_issues(saved) == []
    asset_path(client.app.state.db, asset).unlink()  # Storage loses the file after it was saved.
    missing = [{"field": "musicFiles", "code": "DRAFT_ASSET_MISSING"}]
    edited = patch(client, saved.json(), "unrelated-edit", topic="still editable")
    assert edited.status_code == 200, edited.text
    assert edited.json()["revision"] == 3 and edited.json()["config"]["musicFiles"] == [asset]
    assert asset_issues(edited) == missing
    assert client.get(f"/api/story-drafts/{draft['id']}").json() == edited.json()
    # Duplicate delivery of the accepted edit replays the stored ACK without another revision.
    assert patch(client, saved.json(), "unrelated-edit", topic="still editable").json() == edited.json()
    assert [e["revision"] for e in events(client, draft["id"]) if e["name"] == "draft.saved"] == [1, 2, 3]
    removed = patch(client, edited.json(), musicFiles=[])
    assert removed.status_code == 200 and asset_issues(removed) == []
    # Once removed, the missing file is a new reference again and cannot be re-added.
    readded = patch(client, removed.json(), musicFiles=[asset])
    assert readded.json()["error"]["code"] == "DRAFT_ASSET_MISSING"
    assert client.get(f"/api/story-drafts/{draft['id']}").json()["revision"] == 4


def test_newly_referenced_missing_asset_is_rejected_without_committing(client):
    from smartflow.assets import asset_path

    draft = new_draft(client)
    kept, lost = imported(client, draft["id"]), imported(client, draft["id"])
    draft = patch(client, draft, musicFiles=[kept]).json()
    asset_path(client.app.state.db, lost).unlink()
    before = events(client, draft["id"])
    rejected = patch(client, draft, musicFiles=[kept, lost], topic="must not save")
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "DRAFT_ASSET_MISSING"
    current = client.get(f"/api/story-drafts/{draft['id']}").json()
    assert current == draft and events(client, draft["id"]) == before
    # A rejected command committed nothing, so a fresh snapshot with the same revision saves.
    retried = patch(client, draft, topic="fixed")
    assert retried.status_code == 200 and retried.json()["revision"] == draft["revision"] + 1


def test_duplicate_and_foreign_asset_ids_are_rejected_as_invalid(client):
    draft, other = new_draft(client), new_draft(client)
    asset = imported(client, draft["id"])
    saved = patch(client, draft, musicFiles=[asset]).json()
    for config in (
        {"musicFiles": [asset, asset]},  # Duplicate even though the id was already referenced.
        {"musicFiles": [imported(client, other["id"])]},
        {"sfxFiles": [asset]},  # Imported for a different field.
    ):
        result = patch(client, saved, **config)
        assert result.status_code == 422, result.text
        assert result.json()["error"]["code"] == "DRAFT_ASSET_INVALID"
    assert client.get(f"/api/story-drafts/{draft['id']}").json() == saved


def test_lost_ack_replay_returns_stored_response_after_asset_goes_missing(client):
    from smartflow.assets import asset_path

    draft = new_draft(client)
    asset = imported(client, draft["id"])
    accepted = patch(client, draft, "lost-ack", musicFiles=[asset])
    assert accepted.status_code == 200, accepted.text
    asset_path(client.app.state.db, asset).unlink()
    before = events(client, draft["id"])
    replay = patch(client, draft, "lost-ack", musicFiles=[asset])
    assert replay.status_code == 200 and replay.json() == accepted.json()
    assert events(client, draft["id"]) == before
    assert client.get(f"/api/story-drafts/{draft['id']}").json()["revision"] == 2
    assert patch(client, draft, "lost-ack", topic="other").json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_diagnostic_projection_and_logs_never_include_draft_content(client):
    saved = client.post(
        "/api/story-drafts",
        json={"config": {"topic": "PRIVATE_TITLE", "storyText": "PRIVATE_BODY"}},
        headers=KEY,
    )
    assert saved.status_code == 201
    for url in (
        "/api/diagnostics/drafts",
        f"/api/diagnostics/drafts/{saved.json()['id']}/events",
        "/api/diagnostics/logs",
    ):
        text = client.get(url).text
        assert "PRIVATE_TITLE" not in text and "PRIVATE_BODY" not in text
    logs = (client.app.state.db.path.parent / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert "draft.saved" in logs and "PRIVATE_BODY" not in logs and "PRIVATE_TITLE" not in logs


@pytest.mark.parametrize(
    "role,read,write,diagnostics",
    [
        ("owner", True, True, True),
        ("operator", True, True, False),
        ("viewer", True, False, False),
        ("support", False, False, True),
    ],
)
@pytest.mark.parametrize("mode", ["local_session", "dev_bypass"])
def test_draft_permissions_at_every_route(tmp_path, role, read, write, diagnostics, mode):
    settings = Settings(tmp_path, TOKEN, "test", auth_mode=mode, session_role=role)
    with TestClient(create_app(settings), headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        row = Drafts(client.app.state.db).save(DraftInput(), "seed", str(uuid4()))
        for method, url, body, allowed in [
            ("post", "/api/story-drafts", {}, write),
            ("get", "/api/story-drafts", None, read),
            ("get", f"/api/story-drafts/{row['id']}", None, read),
            ("patch", f"/api/story-drafts/{row['id']}", {"expected_revision": 1}, write),
            ("get", "/api/diagnostics/drafts", None, diagnostics),
            ("get", f"/api/diagnostics/drafts/{row['id']}/events", None, diagnostics),
        ]:
            headers = {"Idempotency-Key": str(uuid4()), "X-Role": "owner"}
            assert (
                client.request(method, url, json=body, headers={**headers, "Authorization": ""}).status_code
                == 401
            )
            response = client.request(method, url, json=body, headers=headers)
            assert response.status_code in ({200, 201} if allowed else {403}), response.text


def test_scope_and_concurrent_writers_cannot_overwrite_each_other(system):
    db, *_ = system
    drafts = Drafts(db)
    row = drafts.save(DraftInput(), "initial", str(uuid4()))
    with pytest.raises(AppError, match="DRAFT_NOT_FOUND"):
        Drafts(db, scope="other-workspace").get(row["id"])

    def save(index):
        try:
            return drafts.save(
                DraftUpdate(expected_revision=1, config={"topic": str(index)}),
                f"write-{index}",
                str(uuid4()),
                row["id"],
            )["revision"]
        except AppError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, [1, 2]))
    assert results.count(2) == 1 and results.count("DRAFT_REVISION_CONFLICT") == 1
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(DraftEvent)) == 2
        assert session.scalar(select(func.count()).select_from(DraftCommand)) == 2
        assert session.scalar(select(func.count()).select_from(StoryDraft)) == 1


def test_draft_transaction_rolls_back_all_records_on_event_failure(system, monkeypatch):
    from sqlalchemy.orm import Session

    db, *_ = system
    original = Session.add

    def fail_event(self, instance, *args, **kwargs):
        if isinstance(instance, DraftEvent):
            raise OSError("PRIVATE_FAILURE")
        return original(self, instance, *args, **kwargs)

    monkeypatch.setattr(Session, "add", fail_event)
    with pytest.raises(OSError):
        Drafts(db).save(DraftInput(), "atomic", str(uuid4()))
    assert Drafts(db).list() == []
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(DraftCommand)) == 0
