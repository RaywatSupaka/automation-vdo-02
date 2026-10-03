import asyncio
import secrets
from uuid import uuid4

import pytest
from smartflow.assets import Assets, asset_path
from smartflow.auth import AuthMode
from smartflow.browser_bridge import COMPAT, Bridge, PairExchange, PairRequest
from smartflow.draft_contracts import REGISTRY, DraftConfig, DraftInput, DraftUpdate
from smartflow.drafts import Drafts
from smartflow.errors import AppError
from smartflow.job_queue import queue_items
from smartflow.story_contracts import Grant, Result, StoryStart, Sync
from smartflow.story_workflow import StoryWorkflow

PNG = b"\x89PNG\r\n\x1a\n" + bytes(40)
MP3 = b"ID3" + bytes(45)


def import_file(db, clock, draft_id, field, name, payload):
    async def stream():
        yield payload

    return asyncio.run(
        Assets(db, clock).import_file(draft_id, field, name, len(payload), str(uuid4()), stream(), "trace")
    )


def test_successor_keeps_settings_resets_story_content_and_clones_setting_files(system):
    db, _, _, clock, _ = system
    drafts = Drafts(db, clock)
    first = drafts.save(DraftInput(config=DraftConfig(topic="PRIVATE ONE")), "d1", "t")
    image = import_file(db, clock, first["id"], "mainImage", "ref.png", PNG)
    music = import_file(db, clock, first["id"], "musicFiles", "song.mp3", MP3)
    config = DraftConfig(
        topic="PRIVATE ONE",
        storyText="private detail",
        tone="ลึกลับ",
        mainImage=[image["id"]],
        musicEnabled=True,
        musicFiles=[music["id"]],
        musicCount="1",
    )
    saved = drafts.save(DraftUpdate(expected_revision=1, config=config), "d2", "t", first["id"])
    clock.advance(5)

    nxt = drafts.successor(first["id"], "next-key", "t")
    assert nxt["id"] != first["id"] and nxt["revision"] == 1 and nxt["active_step"] == 0
    for field, spec in REGISTRY.items():
        if spec.get("perStory"):
            assert nxt["config"][field] == spec["initial"], field
    assert nxt["config"]["tone"] == "ลึกลับ" and nxt["config"]["musicEnabled"] is True
    [clone] = nxt["config"]["musicFiles"]
    assert clone != music["id"] and nxt["config"]["mainImage"] == []
    assert asset_path(db, clone).read_bytes() == MP3
    listed = Assets(db, clock).list(nxt["id"])
    assert [(a["field"], a["sha256"], a["missing"]) for a in listed] == [
        ("musicFiles", music["sha256"], False)
    ]
    assert nxt["issues"] == [] or all(i["code"] != "DRAFT_ASSET_MISSING" for i in nxt["issues"])

    # Lost ACK: the same key replays the same draft without new rows; the source is untouched.
    assert drafts.successor(first["id"], "next-key", "t") == nxt
    assert drafts.get(first["id"]) == drafts.get(saved["id"])
    assert drafts.list(limit=1)[0]["id"] == nxt["id"]  # The new draft is what the UI loads next.
    with pytest.raises(AppError, match="IDEMPOTENCY_CONFLICT"):
        drafts.successor(nxt["id"], "next-key", "t")


def test_successor_skips_a_setting_file_that_went_missing(system):
    db, _, _, clock, _ = system
    drafts = Drafts(db, clock)
    first = drafts.save(DraftInput(config=DraftConfig(topic="x")), "d1", "t")
    logo = import_file(db, clock, first["id"], "logoFile", "logo.png", PNG)
    drafts.save(
        DraftUpdate(
            expected_revision=1, config=DraftConfig(topic="x", logoEnabled=True, logoFile=[logo["id"]])
        ),
        "d2",
        "t",
        first["id"],
    )
    asset_path(db, logo["id"]).unlink()
    nxt = drafts.successor(first["id"], "next", "t")
    assert nxt["config"]["logoFile"] == []
    assert {"field": "logoFile", "code": "FIELD_REQUIRED"} in nxt["issues"]  # User re-picks; nothing blocks.


def pair(system):
    db, _, _, clock, _ = system
    bridge = Bridge(db, AuthMode.LOCAL_SESSION, clock)
    code = bridge.create(PairRequest(extension_id=COMPAT["extension_id"]), "trace")["code"]
    token = secrets.token_urlsafe(32)
    bridge.exchange(
        bridge.authenticate(code),
        PairExchange(
            extension_id=COMPAT["extension_id"],
            extension_version=COMPAT["extension_version"],
            helper_version=COMPAT["helper_version"],
            agent_token=token,
        ),
        "trace",
    )
    sync = Sync(
        action="sync",
        connection_id=uuid4(),
        extension_version=COMPAT["extension_version"],
        helper_version=COMPAT["helper_version"],
        capability="story_simulator_v1",
    )
    return bridge.authenticate(token), sync


def start(system, service, topic, key):
    db, _, _, clock, _ = system
    draft = Drafts(db, clock).save(DraftInput(config=DraftConfig(topic=topic)), key + "-draft", "t")
    return service.create(StoryStart(draft_id=draft["id"], expected_revision=1, mode="simulation"), key, "t")


def owned(task, cls, **extra):
    action = {Grant: "grant", Result: "result"}[cls]
    return cls(
        action=action,
        **{k: task[k] for k in ("connection_id", "operation_id", "request_id", "lease_epoch")},
        **extra,
    )


def statuses(db):
    return [
        (i["title"], i["status"], i["error_code"], i["queue_position"])
        for i in queue_items(db)
        if i["kind"] == "story"
    ]


def test_jobs_queue_in_fifo_order_and_never_expire_while_waiting(system):
    db, _, _, clock, _ = system
    service = StoryWorkflow(db, clock)
    start(system, service, "FIRST", "k1")
    clock.advance(1)
    start(system, service, "SECOND", "k2")
    # No browser yet: both wait, in order, with the one actionable reason.
    assert statuses(db) == [
        ("FIRST", "waiting", "EXTENSION_DISCONNECTED", 0),
        ("SECOND", "waiting", "EXTENSION_DISCONNECTED", 1),
    ]
    clock.advance(5000)  # Far past the 900 s budget while unclaimed.
    service.maintain()
    assert [s[1] for s in statuses(db)] == ["waiting", "waiting"]

    actor, sync = pair(system)
    task = service.sync(actor, sync)["task"]
    assert task["topic"] == "FIRST"
    service.maintain()
    assert statuses(db) == [("FIRST", "running", None, 0), ("SECOND", "queued", None, 1)]
    third = start(system, service, "THIRD", "k3")
    assert third["status"] == "queued" and statuses(db)[-1] == ("THIRD", "queued", None, 2)

    service.grant(actor, owned(task, Grant))
    service.result(actor, owned(task, Result, result="[SIMULATION ONLY]\nFIRST"))
    assert statuses(db)[:2] == [("SECOND", "queued", None, 0), ("THIRD", "queued", None, 1)]
    assert service.detail(third["id"])["queue_position"] == 1
    finished = [i for i in queue_items(db) if i["status"] == "completed"]
    assert [i["title"] for i in finished] == ["FIRST"] and finished[0]["queue_position"] is None


def test_deadline_starts_at_first_claim(system):
    db, _, _, clock, _ = system
    service = StoryWorkflow(db, clock)
    job = start(system, service, "LATE", "k")
    clock.advance(10_000)
    actor, sync = pair(system)
    task = service.sync(actor, sync)["task"]
    assert task and task["mode"] == "dispatch"  # Queued 10 000 s, still dispatchable.
    clock.advance(901 + 91)
    service.maintain()
    assert service.detail(job["id"])["status"] == "failed"  # The budget runs from the claim.


def test_queue_and_successor_http_permissions(client):
    draft = client.post(
        "/api/story-drafts", json={"config": {"topic": "x"}}, headers={"Idempotency-Key": "queue-draft-key"}
    )
    assert client.get("/api/queue").status_code == 200
    created = client.post(
        f"/api/story-drafts/{draft.json()['id']}/successor", headers={"Idempotency-Key": "queue-next-key"}
    )
    assert created.status_code == 201, created.text
    assert (
        client.post(f"/api/story-drafts/{draft.json()['id']}/successor").status_code == 422
    )  # Key required.
