from concurrent.futures import ThreadPoolExecutor

import pytest
from smartflow.db import Database
from smartflow.engine import Engine
from smartflow.errors import AppError
from smartflow.models import Job, Receipt, SimulatedRequest
from smartflow.providers import Simulator
from sqlalchemy import select

pytestmark = pytest.mark.integration


def sends(db):
    with db.transaction() as session:
        return sum(r.sends for r in session.scalars(select(SimulatedRequest)))


def test_success_has_durable_checkpoint_and_atomic_event_sequence(system):
    db, jobs, engine, clock, create = system
    job = create()
    assert engine.tick()
    completed = jobs.get(job["id"])
    assert completed["status"] == "completed"
    assert completed["has_artifact"]
    assert completed["receipt"]["state"] == "completed"
    assert sends(db) == 1
    assert [e["name"] for e in jobs.events(job["id"])][-1] == "artifact.saved"
    assert not engine.tick()


def test_unknown_send_blocks_resume_and_reconciles_without_second_send(system):
    db, jobs, engine, clock, create = system
    job = create("unknown_send")
    engine.tick()
    assert jobs.get(job["id"])["error"]["code"] == "SEND_ACCEPTANCE_UNKNOWN"
    with pytest.raises(AppError, match="SEND_ACCEPTANCE_UNKNOWN"):
        jobs.command(job["id"], "resume")
    engine.reconcile(job["id"])
    engine.tick()
    assert jobs.get(job["id"])["status"] == "completed"
    assert sends(db) == 1


def test_save_failure_resume_uses_existing_result(system):
    db, jobs, engine, clock, create = system
    job = create("save_failure")
    engine.tick()
    assert jobs.get(job["id"])["error"]["code"] == "MEDIA_SAVE_FAILED"
    assert jobs.get(job["id"])["status"] == "waiting"
    clock.advance()
    jobs.command(job["id"], "resume")
    jobs.command(job["id"], "resume")
    engine.tick()
    assert jobs.get(job["id"])["status"] == "completed"
    assert sends(db) == 1


def test_repeated_storage_failure_stops_and_manual_resume_does_not_resend(system, monkeypatch):
    import os

    db, jobs, engine, clock, create = system
    job = create()
    original = os.replace

    def failed_replace(*args):
        raise PermissionError("Private path must not be logged")

    monkeypatch.setattr(os, "replace", failed_replace)
    for _ in range(3):
        engine.tick()
        clock.advance()
    assert jobs.get(job["id"])["status"] == "failed"
    assert not engine.tick()
    monkeypatch.setattr(os, "replace", original)
    jobs.command(job["id"], "resume")
    engine.tick()
    assert jobs.get(job["id"])["status"] == "completed"
    assert sends(db) == 1


def test_retry_clock_is_injected_and_never_sleeps(system):
    db, jobs, engine, clock, create = system
    job = create("transient")
    engine.tick()
    assert jobs.get(job["id"])["status"] == "waiting"
    assert sends(db) == 0
    assert not engine.tick()
    clock.advance()
    engine.tick()
    assert jobs.get(job["id"])["status"] == "completed"
    assert sends(db) == 1


def test_repeated_preflight_failure_exhausts_three_attempts(system):
    db, jobs, engine, clock, create = system

    class Offline(Simulator):
        def preflight(self, scenario, attempt):
            raise AppError("PROVIDER_UNAVAILABLE")

    engine.provider = Offline(db)
    job = create()
    for _ in range(3):
        engine.tick()
        clock.advance()
    assert jobs.get(job["id"])["status"] == "failed"
    assert jobs.get(job["id"])["attempts"] == 3
    assert sends(db) == 0


def test_pending_result_has_bounded_observation_without_resend(system):
    db, jobs, engine, clock, create = system
    job = create("pending")
    for _ in range(3):
        engine.tick()
        clock.advance()
    assert jobs.get(job["id"])["status"] == "needs_review"
    assert jobs.get(job["id"])["observations"] == 3
    assert not engine.tick()
    assert sends(db) == 1


def test_auth_error_is_pre_send(system):
    db, jobs, engine, clock, create = system
    job = create("auth_required")
    engine.tick()
    assert jobs.get(job["id"])["error"]["code"] == "PROVIDER_AUTH_REQUIRED"
    assert jobs.get(job["id"])["receipt"]["state"] == "prepared"
    assert sends(db) == 0


@pytest.mark.parametrize(
    "state,expected",
    [
        ("prepared", "queued"),
        ("accepted", "queued"),
        ("completed", "queued"),
        ("dispatching", "needs_review"),
        ("unknown", "needs_review"),
    ],
)
def test_restart_recovers_by_receipt_evidence(system, state, expected):
    db, jobs, engine, clock, create = system
    job = create()
    with db.transaction(write=True) as session:
        session.get(Job, job["id"]).status = "running"
        session.add(
            Receipt(
                job_id=job["id"],
                request_id="persisted-request",
                state=state,
                updated_at=clock(),
                result="Saved simulation" if state == "completed" else None,
            )
        )
    # New engine and new connection: no in-memory state is used to decide recovery.
    second = Database(db.path, db.logger)
    recovered = Engine(second, Simulator(second), engine.data_dir, clock)
    recovered.recover()
    assert jobs.get(job["id"])["status"] == expected
    if expected == "needs_review":
        assert not recovered.tick()
        assert sends(db) == 0
    second.close()


def test_concurrent_duplicate_create_and_resume_do_not_duplicate_work(system):
    db, jobs, engine, clock, create = system
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: create(), range(4)))
    assert len({r["id"] for r in results}) == 1
    with pytest.raises(AppError, match="IDEMPOTENCY_CONFLICT"):
        create(title="Different input")
    engine.tick()
    jobs.command(results[0]["id"], "resume")
    assert not engine.tick()
    assert sends(db) == 1


def test_cancel_during_send_keeps_receipt_and_prevents_followup_work(system):
    db, jobs, engine, clock, create = system
    job = create()

    class Cancelling(Simulator):
        def submit(self, request_id, scenario):
            super().submit(request_id, scenario)
            jobs.command(job["id"], "cancel")

    engine.provider = Cancelling(db)
    engine.tick()
    result = jobs.get(job["id"])
    assert result["status"] == "cancelled"
    assert result["receipt"]["state"] == "accepted"
    assert not result["has_artifact"]
    jobs.command(job["id"], "resume")
    engine.tick()
    assert jobs.get(job["id"])["status"] == "completed"
    assert sends(db) == 1


def test_unexpected_postsend_exception_is_unknown_and_sanitized(system):
    db, jobs, engine, clock, create = system

    class Crashing(Simulator):
        def submit(self, request_id, scenario):
            super().submit(request_id, scenario)
            raise RuntimeError("PRIVATE_TOKEN_AND_PROMPT")

    engine.provider = Crashing(db)
    job = create()
    engine.tick()
    assert jobs.get(job["id"])["error"]["code"] == "SEND_ACCEPTANCE_UNKNOWN"
    evidence = str(jobs.events(job["id"]))
    assert "RuntimeError" in evidence
    assert "PRIVATE_TOKEN_AND_PROMPT" not in evidence
    assert sends(db) == 1


def test_uncommitted_event_rolls_back_with_job_state(system):
    from smartflow.jobs import record

    db, jobs, engine, clock, create = system
    job = create()
    with pytest.raises(RuntimeError):
        with db.transaction(write=True) as session:
            item = session.get(Job, job["id"])
            item.status = "completed"
            record(session, item, "should.rollback", clock())
            raise RuntimeError()
    assert jobs.get(job["id"])["status"] == "queued"
    assert "should.rollback" not in str(jobs.events(job["id"]))
