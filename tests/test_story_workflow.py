import json
import secrets
from uuid import uuid4

import pytest
from smartflow.auth import AuthMode
from smartflow.browser_bridge import COMPAT, Bridge, PairExchange, PairRequest
from smartflow.draft_contracts import DraftConfig, DraftInput, DraftUpdate
from smartflow.drafts import Drafts
from smartflow.errors import AppError
from smartflow.jobs import Jobs
from smartflow.models import Job
from smartflow.story_contracts import Grant, Missing, Result, StoryStart, Sync
from smartflow.story_models import OperationReceipt, StoryRevision
from smartflow.story_workflow import StoryWorkflow
from sqlalchemy import select


def setup(system):
    db, jobs, engine, clock, _ = system
    bridge = Bridge(db, AuthMode.LOCAL_SESSION, clock)
    pair = bridge.create(PairRequest(extension_id=COMPAT["extension_id"]), "pair-trace")
    token = secrets.token_urlsafe(32)
    bridge.exchange(
        bridge.authenticate(pair["code"]),
        PairExchange(
            extension_id=COMPAT["extension_id"],
            extension_version="0.2.0",
            helper_version="0.2.0",
            agent_token=token,
        ),
        "pair-trace",
    )
    principal = bridge.authenticate(token)
    drafts = Drafts(db, clock)
    draft = drafts.save(DraftInput(config=DraftConfig(topic="PRIVATE STORY")), "seed-draft", "draft-trace")
    service = StoryWorkflow(db, clock)
    start = StoryStart(draft_id=draft["id"], expected_revision=draft["revision"], mode="simulation")
    job = service.create(start, "story-create-key", "story-trace")
    sync = Sync(
        action="sync",
        connection_id=uuid4(),
        extension_version="0.2.0",
        helper_version="0.2.0",
        capability="story_simulator_v1",
    )
    return service, principal, sync, job, draft, start


def command(task, cls=Grant, **extra):
    action = {Grant: "grant", Result: "result", Missing: "missing"}[cls]
    return cls(
        action=action,
        **{key: task[key] for key in ("connection_id", "operation_id", "request_id", "lease_epoch")},
        **extra,
    )


def test_snapshot_create_is_idempotent_and_worker_cannot_execute_browser_job(system):
    service, actor, sync, job, draft, start = setup(system)
    db, _, engine, clock, _ = system
    assert service.create(start, "story-create-key", "other-trace")["id"] == job["id"]
    Drafts(db, clock).save(
        DraftUpdate(expected_revision=1, config=DraftConfig(topic="NEW PRIVATE TOPIC")),
        "draft-change",
        "trace",
        draft["id"],
    )
    assert not engine.tick()
    task = service.sync(actor, sync)["task"]
    assert task["topic"] == "PRIVATE STORY" and task["mode"] == "dispatch"
    assert service.detail(job["id"])["draft_revision"] == 1
    with db.transaction() as session:
        assert len(list(session.scalars(select(Job)))) == 1
        assert json.loads(session.scalar(select(StoryRevision)).config)["topic"] == "PRIVATE STORY"
    assert service.grant(actor, command(task))["granted"]
    assert not service.grant(actor, command(task))["granted"]
    assert service.sync(actor, sync)["task"]["mode"] == "inspect"


def test_result_duplicate_ack_and_cancel_preserve_artifact_without_repeat(system):
    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    service.grant(actor, command(task))
    service.command(job["id"], "cancel", "cancel-trace")
    result = command(task, Result, result="[SIMULATION ONLY]\nPRIVATE STORY")
    saved = service.result(actor, result)
    assert saved["persisted"] and service.result(actor, result) == saved
    detail = service.detail(job["id"])
    assert detail["status"] == "cancelled" and detail["receipt_state"] == "completed"
    assert detail["result"] == result.result
    assert service.detail(job["id"], private=False)["result"] is None
    events = Jobs(system[0]).events(job["id"])
    assert sum(event["name"] == "story.artifact_persisted" for event in events) == 1
    logs = (system[0].path.parent / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert "PRIVATE STORY" not in logs and "operation_id" in logs


def test_expired_lease_fences_old_grant_and_unknown_never_dispatches_again(system):
    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    assert service.grant(actor, command(task))["granted"]
    system[3].advance(91)
    service = StoryWorkflow(system[0], system[3])  # Same durable state in a restarted runtime.
    service.maintain()
    with pytest.raises(AppError, match="OPERATION_LEASE_EXPIRED"):
        service.grant(actor, command(task))
    recovered = service.sync(actor, sync)["task"]
    assert recovered["mode"] == "inspect" and recovered["lease_epoch"] > task["lease_epoch"]
    assert not service.grant(actor, command(recovered))["granted"]
    for _ in range(3):
        service.missing(actor, command(recovered, Missing))
    assert service.sync(actor, sync)["task"] is None
    with pytest.raises(AppError, match="SEND_ACCEPTANCE_UNKNOWN"):
        service.command(job["id"], "resume", "trace")
    service.command(job["id"], "reconcile", "trace")
    assert service.sync(actor, sync)["task"]["mode"] == "inspect"


def test_pre_dispatch_retry_has_budget_and_cannot_steal_current_connection(system):
    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    with pytest.raises(AppError, match="BROWSER_CONNECTION_BUSY"):
        service.sync(actor, sync.model_copy(update={"connection_id": uuid4()}))
    for _ in range(2):
        system[3].advance(91)
        task = service.sync(actor, sync)["task"]
        assert task["mode"] == "dispatch"
    system[3].advance(91)
    assert service.sync(actor, sync)["task"] is None
    assert service.detail(job["id"])["error_code"] == "BROWSER_RETRY_EXHAUSTED"


def test_cross_request_bad_result_and_explicit_simulation_contract(system):
    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    with pytest.raises(AppError, match="OPERATION_OWNERSHIP_MISMATCH"):
        service.grant(actor, command(task).model_copy(update={"request_id": uuid4()}))
    with pytest.raises(AppError, match="INVALID_TRANSITION"):
        service.result(actor, command(task, Result, result="[SIMULATION ONLY]\nPRIVATE STORY"))
    service.grant(actor, command(task))
    with pytest.raises(AppError, match="STORY_RESULT_INVALID"):
        service.result(actor, command(task, Result, result="unrelated output"))
    assert service.detail(job["id"])["receipt_state"] == "dispatching"


def test_artifact_write_failure_retries_saved_result_only_with_bounded_budget(system, monkeypatch):
    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    service.grant(actor, command(task))
    import smartflow.story_workflow as module

    real = module.os.replace

    def broken(*args):
        raise OSError("private path must not be logged")

    monkeypatch.setattr(module.os, "replace", broken)
    assert not service.result(actor, command(task, Result, result="[SIMULATION ONLY]\nPRIVATE STORY"))[
        "persisted"
    ]
    for _ in range(5):
        system[3].advance(10)
        service.maintain()
    with system[0].transaction() as session:
        assert session.get(Job, job["id"]).save_attempts == 3
        assert session.get(OperationReceipt, task["operation_id"]).state == "accepted"
    assert service.detail(job["id"])["status"] == "failed"
    monkeypatch.setattr(module.os, "replace", real)
    service.command(job["id"], "resume", "trace")
    service.maintain()
    assert service.detail(job["id"])["receipt_state"] == "completed"
    assert service.sync(actor, sync)["task"] is None


def test_http_work_requires_paired_agent_not_owner_and_story_is_readable(client):
    draft = client.post(
        "/api/story-drafts",
        json={"config": {"topic": "story API"}},
        headers={"Idempotency-Key": "story-api-draft"},
    ).json()
    created = client.post(
        "/api/stories",
        json={"draft_id": draft["id"], "expected_revision": 1, "mode": "simulation"},
        headers={"Idempotency-Key": "story-api-create"},
    )
    assert created.status_code == 201, created.text
    job = created.json()
    assert client.get(f"/api/stories/{job['id']}").status_code == 200
    assert client.get(f"/api/diagnostics/stories/{job['id']}").json().get("result") is None
    assert client.post("/api/browser/work", json={}).status_code == 403
    assert (
        client.post(
            "/api/jobs",
            json={"title": "bypass", "scenario": "story_simulated"},
            headers={"Idempotency-Key": "reject-direct-story"},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("after_grant", [False, True])
def test_agent_storage_failure_is_persisted_and_stops_automatic_dispatch(system, after_grant):
    from smartflow.story_contracts import Blocked

    service, actor, sync, job, *_ = setup(system)
    task = service.sync(actor, sync)["task"]
    if after_grant:
        service.grant(actor, command(task))
    service.blocked(
        actor,
        Blocked(
            action="blocked", code="EXTENSION_STORAGE_FAILED", **command(task).model_dump(exclude={"action"})
        ),
    )
    detail = service.detail(job["id"])
    assert detail["error_code"] == "EXTENSION_STORAGE_FAILED"
    assert detail["status"] == ("needs_review" if after_grant else "failed")
    assert service.sync(actor, sync)["task"] is None
    if after_grant:
        with pytest.raises(AppError, match="SEND_ACCEPTANCE_UNKNOWN"):
            service.command(job["id"], "resume", "trace")
