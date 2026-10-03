import time

import pytest
from smartflow.config import Settings
from smartflow.jobs import CreateJob, Jobs
from smartflow.models import SimulatedRequest
from smartflow.runtime import runtime

pytestmark = pytest.mark.integration


def until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.025)
    raise AssertionError("Bounded worker observation expired")


def test_real_worker_process_recovers_after_termination_without_resend(tmp_path):
    with runtime(Settings(tmp_path, "runtime-test-session-not-secret", "test")) as app:
        jobs = Jobs(app.state.db)
        job = jobs.create(
            CreateJob(title="Process crash", scenario="unknown_send"), "crash-test", "crash-trace"
        )
        until(lambda: jobs.get(job["id"])["status"] == "needs_review")
        original = app.state.worker_process()
        original.terminate()
        original.join(timeout=3)
        until(lambda: app.state.worker_process().pid != original.pid and app.state.worker_alive())
        assert jobs.get(job["id"])["status"] == "needs_review"
        receipt = jobs.get(job["id"])["receipt"]
        with app.state.db.transaction() as session:
            assert session.get(SimulatedRequest, receipt["request_id"]).sends == 1


def test_real_worker_reports_ready_from_heartbeat_not_only_process(tmp_path):
    with runtime(Settings(tmp_path, "runtime-test-session-not-secret", "test")) as app:
        until(lambda: app.state.worker_status()[0] == "ready")
        state, age = app.state.worker_status()
        assert app.state.worker_alive() and age is not None and age <= 5
        original = app.state.worker_process()
        original.terminate()
        original.join(timeout=3)
        # The old beat belongs to a dead pid: never reported ready for the replacement.
        until(lambda: app.state.worker_process().pid != original.pid)
        assert app.state.worker_status()[0] in {"starting", "ready", "down"}
        until(lambda: app.state.worker_status()[0] == "ready")
