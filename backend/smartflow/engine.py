import os
import time
from uuid import uuid4

from sqlalchemy import select

from smartflow.errors import AppError
from smartflow.jobs import record
from smartflow.models import Job, Receipt
from smartflow.observability import safe_exception


class Engine:
    """One worker owns this engine; API commands use serialized DB transactions."""

    def __init__(self, db, provider, data_dir, clock=time.time):
        self.db, self.provider, self.data_dir, self.clock = db, provider, data_dir, clock

    def recover(self):
        with self.db.transaction(write=True) as session:
            for job in session.scalars(select(Job).where(Job.status == "running")):
                receipt = session.get(Receipt, job.id)
                uncertain = receipt and receipt.state in {"dispatching", "unknown"}
                job.status = "needs_review" if uncertain else "queued"
                job.error_code = "SEND_ACCEPTANCE_UNKNOWN" if uncertain else "WORKER_INTERRUPTED"
                job.updated_at = self.clock()
                record(session, job, "worker.recovered", self.clock(), job.error_code)

    def claim(self):
        with self.db.transaction(write=True) as session:
            job = session.scalar(
                select(Job)
                .where(Job.status.in_(["queued", "waiting"]), Job.next_run_at <= self.clock())
                .order_by(Job.created_at)
                .limit(1)
            )
            if not job:
                return None
            job.status, job.error_code = "running", None
            job.updated_at = self.clock()
            record(session, job, "worker.claimed", self.clock())
            return job.id

    def tick(self):
        job_id = self.claim()
        if job_id is None:
            return False
        try:
            self.execute(job_id)
        except Exception as exc:
            # Unknown exceptions after the durable dispatch marker cannot authorize replay.
            with self.db.transaction(write=True) as session:
                job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
                uncertain = receipt and receipt.state in {"dispatching", "unknown"}
                code = "SEND_ACCEPTANCE_UNKNOWN" if uncertain else "INTERNAL_ERROR"
                if uncertain:
                    receipt.state = "unknown"
                if job.status != "cancelled":
                    job.status, job.error_code = "needs_review" if uncertain else "failed", code
                record(session, job, "worker.exception", self.clock(), code, **safe_exception(exc))
        return True

    def execute(self, job_id):
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            if job.status != "running":
                return
            receipt = session.get(Receipt, job_id)
            if not receipt:
                receipt = Receipt(
                    job_id=job_id, request_id=str(uuid4()), state="prepared", updated_at=self.clock()
                )
                session.add(receipt)
                record(session, job, "request.prepared", self.clock())
            state, request_id, scenario = receipt.state, receipt.request_id, job.scenario
            if state in {"unknown", "dispatching"}:
                job.status, job.error_code = "needs_review", "SEND_ACCEPTANCE_UNKNOWN"
                record(session, job, "request.review_required", self.clock(), job.error_code)
                return
            if state == "prepared":
                job.attempts += 1
                attempt = job.attempts
        if state == "prepared":
            try:
                self.provider.preflight(scenario, attempt)
            except AppError as exc:
                self.fail_before_send(job_id, exc.code, attempt)
                return
            with self.db.transaction(write=True) as session:
                job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
                if job.status != "running":
                    return
                job.stage, receipt.state, receipt.updated_at = "generate", "dispatching", self.clock()
                record(session, job, "request.dispatching", self.clock())
            # The dispatch boundary is committed before this external side effect.
            try:
                self.provider.submit(request_id, scenario)
            except AppError:
                with self.db.transaction(write=True) as session:
                    job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
                    receipt.state, receipt.updated_at = "unknown", self.clock()
                    if job.status != "cancelled":
                        job.status, job.error_code = "needs_review", "SEND_ACCEPTANCE_UNKNOWN"
                    record(session, job, "request.unknown", self.clock(), "SEND_ACCEPTANCE_UNKNOWN")
                return
            with self.db.transaction(write=True) as session:
                job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
                receipt.state, receipt.updated_at = "accepted", self.clock()
                record(session, job, "request.accepted", self.clock())
        self.collect(job_id, request_id, scenario)

    def fail_before_send(self, job_id, code, attempt):
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            if job.status == "cancelled":
                return
            retry = code == "PROVIDER_UNAVAILABLE" and attempt < 3
            job.status = "waiting" if retry else "failed"
            job.error_code, job.updated_at = code, self.clock()
            job.next_run_at = self.clock() + min(2 ** (attempt - 1), 4)
            record(session, job, "preflight.failed", self.clock(), code, attempt=attempt, will_retry=retry)

    def collect(self, job_id, request_id, scenario):
        with self.db.transaction() as session:
            job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
            if job.status == "cancelled":
                return
            result = receipt.result
        if result is None:
            result = self.provider.inspect(request_id, scenario)
            with self.db.transaction(write=True) as session:
                job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
                if result is None:
                    job.observations += 1
                    if job.status != "cancelled":
                        job.status = "needs_review" if job.observations >= 3 else "waiting"
                        job.error_code = "RESULT_PENDING"
                        job.next_run_at = self.clock() + 2
                    record(
                        session,
                        job,
                        "result.pending",
                        self.clock(),
                        "RESULT_PENDING",
                        observation=job.observations,
                    )
                    return
                receipt.result, receipt.state, receipt.updated_at = result, "completed", self.clock()
                record(session, job, "result.collected", self.clock())
        self.save(job_id, result, scenario)

    def save(self, job_id, result, scenario):
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            if job.status == "cancelled":
                return
            job.stage = "save"
            job.save_attempts += 1
            attempt = job.save_attempts
            record(session, job, "artifact.saving", self.clock())
        target = self.data_dir / "artifacts" / job_id / "simulation.txt"
        temporary = target.with_suffix(".tmp")
        try:
            if scenario == "save_failure" and attempt == 1:
                raise OSError("Simulated storage fault")
            target.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(result)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except OSError:
            with self.db.transaction(write=True) as session:
                job = session.get(Job, job_id)
                if job.status != "cancelled":
                    job.status = "waiting" if attempt < 3 else "failed"
                    job.error_code = "MEDIA_SAVE_FAILED"
                    job.next_run_at = self.clock() + min(2 ** (attempt - 1), 4)
                record(
                    session, job, "artifact.failed", self.clock(), "MEDIA_SAVE_FAILED", will_retry=attempt < 3
                )
            return
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            job.artifact = target.relative_to(self.data_dir).as_posix()
            if job.status != "cancelled":
                job.status, job.stage, job.error_code = "completed", "done", None
            job.updated_at = self.clock()
            record(session, job, "artifact.saved", self.clock())

    def reconcile(self, job_id):
        with self.db.transaction() as session:
            job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
            if not job:
                raise AppError("JOB_NOT_FOUND")
            if not receipt or job.status not in {"needs_review", "cancelled"}:
                raise AppError("INVALID_TRANSITION")
            request_id, scenario = receipt.request_id, job.scenario
        result = self.provider.inspect(request_id, scenario)  # Read only: never calls submit.
        with self.db.transaction(write=True) as session:
            job, receipt = session.get(Job, job_id), session.get(Receipt, job_id)
            if job.status not in {"needs_review", "cancelled"}:
                return
            record(
                session,
                job,
                "request.observed",
                self.clock(),
                None if result is not None else "RESULT_PENDING",
                result_found=result is not None,
            )
            if result is not None:
                receipt.state, receipt.result, receipt.updated_at = "completed", result, self.clock()
                if job.status != "cancelled":
                    job.status, job.error_code, job.next_run_at = "queued", None, self.clock()
