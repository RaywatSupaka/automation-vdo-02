import hashlib
import json
import time
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from smartflow.errors import AppError, error_payload
from smartflow.models import Event, Job, Receipt

Scenario = Literal["success", "auth_required", "unknown_send", "save_failure", "transient", "pending"]


class CreateJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    scenario: Scenario = "success"

    @field_validator("title")
    @classmethod
    def valid_title(cls, value):
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value.strip()


def record(session, job, name, now, code=None, **details):
    event = Event(
        job_id=job.id,
        trace_id=job.trace_id,
        at=now,
        name=name,
        stage=job.stage,
        code=code,
        details=json.dumps(details, ensure_ascii=False),
    )
    session.add(event)
    session.flush()
    session.info.setdefault("events", []).append(
        {
            "job_id": job.id,
            "trace_id": job.trace_id,
            "stage": job.stage,
            "code": code,
            "status": job.status,
            "event_id": event.id,
            "command_trace_id": details.get("command_trace_id"),
            **{
                key: details[key]
                for key in ("operation_id", "request_id", "revision_id", "lease_epoch")
                if key in details
            },
        }
    )


def job_view(job, receipt=None, private=True):
    result = {
        key: getattr(job, key)
        for key in (
            "id",
            "status",
            "stage",
            "trace_id",
            "attempts",
            "save_attempts",
            "observations",
            "created_at",
            "updated_at",
            "next_run_at",
        )
    }
    result.update(
        provider="simulator",
        simulation=True,
        error=error_payload(job.error_code, job.trace_id, job.stage) if job.error_code else None,
        receipt={"state": receipt.state, "request_id": receipt.request_id} if receipt else None,
        has_artifact=bool(job.artifact),
    )
    if private:
        result.update(title=job.title, scenario=job.scenario)
    return result


class Jobs:
    def __init__(self, db, clock=time.time, mode="dev"):
        self.db, self.clock, self.mode = db, clock, mode

    def create(self, data: CreateJob, command_key: str, trace_id: str):
        if self.mode == "prod" and data.scenario != "success":
            raise AppError("SCENARIO_NOT_ALLOWED")
        fingerprint = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        with self.db.transaction(write=True) as session:
            existing = session.scalar(select(Job).where(Job.command_key == command_key))
            if existing:
                if existing.input_hash != fingerprint:
                    raise AppError("IDEMPOTENCY_CONFLICT")
                return job_view(existing, session.get(Receipt, existing.id))
            now = self.clock()
            job = Job(
                id=str(uuid4()),
                command_key=command_key,
                input_hash=fingerprint,
                title=data.title,
                scenario=data.scenario,
                status="queued",
                stage="prepare",
                trace_id=trace_id,
                attempts=0,
                save_attempts=0,
                observations=0,
                next_run_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            session.flush()
            record(session, job, "job.created", now)
            return job_view(job)

    def receipt(self, session, job):
        from smartflow.story_workflow import operation_receipt

        return operation_receipt(session, job)

    def list(self, limit=100, offset=0):
        with self.db.transaction() as session:
            return [
                job_view(j, self.receipt(session, j))
                for j in session.scalars(
                    select(Job).order_by(Job.created_at.desc(), Job.id.desc()).offset(offset).limit(limit)
                )
            ]

    def get(self, job_id, private=True):
        with self.db.transaction() as session:
            job = session.get(Job, job_id)
            if not job:
                raise AppError("JOB_NOT_FOUND")
            return job_view(job, self.receipt(session, job), private)

    def events(self, job_id, after=0, limit=200):
        self.get(job_id)
        with self.db.transaction() as session:
            return [
                {
                    "id": e.id,
                    "at": e.at,
                    "name": e.name,
                    "stage": e.stage,
                    "trace_id": e.trace_id,
                    "code": e.code,
                    "details": json.loads(e.details),
                }
                for e in session.scalars(
                    select(Event)
                    .where(Event.job_id == job_id, Event.id > after)
                    .order_by(Event.id)
                    .limit(limit)
                )
            ]

    def command(self, job_id, action, command_trace_id=None):
        if action not in {"resume", "cancel"}:
            raise AppError("INVALID_TRANSITION")
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            if not job:
                raise AppError("JOB_NOT_FOUND")
            receipt = session.get(Receipt, job_id)
            details = {"command_trace_id": command_trace_id} if command_trace_id else {}
            if action == "cancel":
                if job.status in {"completed", "cancelled"}:
                    record(
                        session,
                        job,
                        "job.command_noop",
                        self.clock(),
                        action=action,
                        outcome="noop",
                        **details,
                    )
                    return job_view(job, receipt)
                job.status = "cancelled"
            else:
                if job.status in {"queued", "running", "waiting", "completed"}:
                    record(
                        session,
                        job,
                        "job.command_noop",
                        self.clock(),
                        action=action,
                        outcome="noop",
                        **details,
                    )
                    return job_view(job, receipt)
                if receipt and receipt.state in {"dispatching", "unknown"}:
                    raise AppError("SEND_ACCEPTANCE_UNKNOWN")
                job.status, job.error_code, job.next_run_at = "queued", None, self.clock()
                job.observations = 0
            job.updated_at = self.clock()
            record(session, job, f"job.{action}", self.clock(), action=action, outcome="applied", **details)
            return job_view(job, receipt)
