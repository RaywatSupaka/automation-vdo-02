"""One simulated browser operation per immutable Story revision. No real provider sends."""

import hashlib
import json
import os
import time
from uuid import uuid4

from filelock import FileLock, Timeout
from sqlalchemy import or_, select

from smartflow.auth import Role
from smartflow.browser_bridge import COMPAT, Pairing
from smartflow.draft_contracts import REGISTRY, issues
from smartflow.drafts import Drafts, digest
from smartflow.errors import AppError
from smartflow.jobs import job_view, record
from smartflow.models import Job
from smartflow.story_models import BrowserSession, OperationReceipt, StoryOperation, StoryRevision

LEASE_SECONDS = 90
MAX_ATTEMPTS = 3


def operation_receipt(session, job):
    if job.scenario != "story_simulated":
        from smartflow.models import Receipt

        return session.get(Receipt, job.id)
    op = session.scalar(select(StoryOperation).where(StoryOperation.job_id == job.id))
    return session.get(OperationReceipt, op.id) if op else None


class StoryWorkflow:
    def __init__(self, db, clock=time.time):
        self.db, self.clock = db, clock

    def create(self, data, key, trace):
        command_key = "story:" + hashlib.sha256(key.encode()).hexdigest()
        fingerprint = digest(data.model_dump(mode="json"))
        with self.db.transaction(write=True) as session:
            existing = session.scalar(select(Job).where(Job.command_key == command_key))
            if existing:
                if existing.input_hash != fingerprint:
                    raise AppError("IDEMPOTENCY_CONFLICT")
                return job_view(existing, operation_receipt(session, existing))
            draft = Drafts(self.db).owned(session, str(data.draft_id))
            if draft.revision != data.expected_revision:
                raise AppError("DRAFT_REVISION_CONFLICT")
            config = json.loads(draft.config)
            if config["creationMode"] != "single":
                raise AppError("STORY_CAPABILITY_UNAVAILABLE")
            if not config["topic"].strip() or issues(config):
                raise AppError("STORY_DRAFT_INVALID")
            from smartflow.asset_models import DraftAsset
            from smartflow.assets import Assets

            for field, spec in REGISTRY.items():
                if spec["kind"] == "file":
                    for asset_id in config[field]:
                        asset = session.get(DraftAsset, asset_id)
                        if not asset or asset.field != field:
                            raise AppError("DRAFT_ASSET_INVALID")
                        Assets(self.db).verified_path(draft.id, asset_id)
            now = self.clock()
            job = Job(
                id=str(uuid4()),
                command_key=command_key,
                input_hash=fingerprint,
                title=config["topic"].strip()[:120],
                scenario="story_simulated",
                status="waiting",
                stage="prepare",
                error_code="EXTENSION_DISCONNECTED",
                trace_id=trace,
                attempts=0,
                save_attempts=0,
                observations=0,
                next_run_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            session.flush()
            revision = StoryRevision(
                id=str(uuid4()),
                job_id=job.id,
                draft_id=draft.id,
                draft_revision=draft.revision,
                config=draft.config,
            )
            session.add(revision)
            session.flush()
            op = StoryOperation(
                id=str(uuid4()),
                job_id=job.id,
                revision_id=revision.id,
                lease_epoch=0,
                lease_until=0,
                deadline=now + 900,
            )
            session.add(op)
            session.flush()
            receipt = OperationReceipt(
                operation_id=op.id, request_id=str(uuid4()), state="prepared", updated_at=now
            )
            session.add(receipt)
            record(
                session,
                job,
                "story.snapshot_created",
                now,
                operation_id=op.id,
                revision_id=revision.id,
                request_id=receipt.request_id,
            )
            return job_view(job, receipt)

    def detail(self, job_id, private=True):
        with self.db.transaction() as session:
            job = session.get(Job, job_id)
            op = session.scalar(select(StoryOperation).where(StoryOperation.job_id == job_id))
            if not job or not op:
                raise AppError("JOB_NOT_FOUND")
            rev = session.get(StoryRevision, op.revision_id)
            receipt = session.get(OperationReceipt, op.id)
            return dict(
                job_id=job.id,
                revision_id=rev.id,
                draft_id=rev.draft_id,
                draft_revision=rev.draft_revision,
                operation_id=op.id,
                request_id=receipt.request_id,
                receipt_state=receipt.state,
                lease_epoch=op.lease_epoch,
                lease_until=op.lease_until,
                status=job.status,
                error_code=job.error_code,
                trace_id=job.trace_id,
                simulation=True,
                result=receipt.result if private and receipt.state == "completed" else None,
                sha256=receipt.sha256,
            )

    def actor(self, session, identity):
        pair = session.get(Pairing, identity.actor_id)
        if identity.role != Role.BROWSER_AGENT or not pair or pair.state != "paired":
            raise AppError("PERMISSION_DENIED")
        return pair

    def sync(self, identity, data):
        if (
            data.extension_version != COMPAT["extension_version"]
            or data.helper_version != COMPAT["helper_version"]
        ):
            raise AppError("EXTENSION_VERSION_MISMATCH")
        self.maintain()
        now, connection = self.clock(), str(data.connection_id)
        with self.db.transaction(write=True) as session:
            pair = self.actor(session, identity)
            current = session.get(BrowserSession, pair.id)
            if current and current.connection_id != connection and current.last_seen + LEASE_SECONDS > now:
                raise AppError("BROWSER_CONNECTION_BUSY")
            if not current:
                current = BrowserSession(pair_id=pair.id, connection_id=connection, last_seen=now)
                session.add(current)
            current.connection_id, current.last_seen, pair.last_seen = connection, now, now
            operations = list(
                session.scalars(
                    select(StoryOperation)
                    .join(Job)
                    .where(
                        or_(StoryOperation.pair_id == pair.id, StoryOperation.pair_id.is_(None)),
                        Job.status != "completed",
                    )
                    .order_by(Job.created_at, Job.id)
                )
            )
            # An unresolved owned operation blocks later dispatches for this browser.
            operations.sort(key=lambda row: row.pair_id != pair.id)
            for op in operations:
                job, receipt = session.get(Job, op.job_id), session.get(OperationReceipt, op.id)
                if job.status == "cancelled" and receipt.state == "prepared":
                    continue
                if receipt.state == "completed" or receipt.result is not None:
                    continue
                if job.status == "failed":
                    continue
                if job.observations >= MAX_ATTEMPTS or now >= op.deadline:
                    if op.pair_id == pair.id:
                        return {"task": None}
                    continue
                if op.connection_id != connection or op.lease_until <= now:
                    if receipt.state == "prepared" and job.attempts >= MAX_ATTEMPTS:
                        job.status, job.error_code = "failed", "BROWSER_RETRY_EXHAUSTED"
                        record(session, job, "story.retry_exhausted", now, job.error_code, operation_id=op.id)
                        continue
                    op.lease_epoch += 1
                    op.pair_id, op.connection_id = pair.id, connection
                    if receipt.state == "prepared":
                        job.attempts += 1
                    record(session, job, "story.claimed", now, operation_id=op.id, lease_epoch=op.lease_epoch)
                op.lease_until = now + LEASE_SECONDS
                if receipt.state == "prepared":
                    job.status, job.error_code = "running", None
                elif job.status != "cancelled":
                    job.status = "needs_review"
                job.updated_at = now
                rev = session.get(StoryRevision, op.revision_id)
                return {
                    "task": dict(
                        operation_id=op.id,
                        request_id=receipt.request_id,
                        job_id=job.id,
                        revision_id=rev.id,
                        trace_id=job.trace_id,
                        connection_id=connection,
                        lease_epoch=op.lease_epoch,
                        lease_until=op.lease_until,
                        mode="dispatch" if receipt.state == "prepared" else "inspect",
                        simulation=True,
                        topic=json.loads(rev.config)["topic"],
                    )
                }
            return {"task": None}

    def owned(self, session, identity, command):
        self.actor(session, identity)
        op = session.get(StoryOperation, str(command.operation_id))
        if not op or op.pair_id != identity.actor_id:
            raise AppError("OPERATION_OWNERSHIP_MISMATCH")
        current = session.get(BrowserSession, identity.actor_id)
        if (
            op.connection_id != str(command.connection_id)
            or op.lease_epoch != command.lease_epoch
            or not current
            or current.connection_id != str(command.connection_id)
            or op.lease_until <= self.clock()
        ):
            raise AppError("OPERATION_LEASE_EXPIRED")
        receipt = session.get(OperationReceipt, op.id)
        if receipt.request_id != str(command.request_id):
            raise AppError("OPERATION_OWNERSHIP_MISMATCH")
        return op, session.get(Job, op.job_id), receipt

    def grant(self, identity, data):
        with self.db.transaction(write=True) as session:
            op, job, receipt = self.owned(session, identity, data)
            if job.status == "cancelled" or self.clock() >= op.deadline:
                raise AppError("INVALID_TRANSITION")
            if receipt.state != "prepared":
                return {"granted": False}  # Even an identical retry never reissues send authority.
            receipt.state, receipt.updated_at = "dispatching", self.clock()
            job.stage, job.updated_at = "generate", self.clock()
            record(
                session,
                job,
                "story.dispatch_marked",
                self.clock(),
                operation_id=op.id,
                request_id=receipt.request_id,
                lease_epoch=op.lease_epoch,
            )
            return {"granted": True, "lease_until": op.lease_until}

    def result(self, identity, data):
        with self.db.transaction(write=True) as session:
            op, job, receipt = self.owned(session, identity, data)
            if receipt.state == "prepared":
                raise AppError("INVALID_TRANSITION")
            rev = session.get(StoryRevision, op.revision_id)
            expected = "[SIMULATION ONLY]\n" + json.loads(rev.config)["topic"]
            if data.result != expected:
                raise AppError("STORY_RESULT_INVALID")
            checksum = hashlib.sha256(data.result.encode()).hexdigest()
            if receipt.sha256 and receipt.sha256 != checksum:
                raise AppError("IDEMPOTENCY_CONFLICT")
            if receipt.result is None:
                receipt.state, receipt.result, receipt.sha256 = "accepted", data.result, checksum
                receipt.updated_at = self.clock()
                job.stage, job.next_run_at = "save", self.clock()
                record(session, job, "story.result_collected", self.clock(), operation_id=op.id)
            identifier = op.id
        self.persist(identifier)
        with self.db.transaction() as session:
            receipt = session.get(OperationReceipt, identifier)
            return {"persisted": receipt.state == "completed", "sha256": receipt.sha256}

    def missing(self, identity, data):
        with self.db.transaction(write=True) as session:
            op, job, receipt = self.owned(session, identity, data)
            if receipt.state in {"completed", "prepared"} or receipt.result is not None:
                raise AppError("INVALID_TRANSITION")
            receipt.state, receipt.updated_at = "unknown", self.clock()
            job.observations = min(MAX_ATTEMPTS, job.observations + 1)
            if job.status != "cancelled":
                job.status, job.error_code = "needs_review", "SEND_ACCEPTANCE_UNKNOWN"
            record(
                session,
                job,
                "story.inspect_missing",
                self.clock(),
                "SEND_ACCEPTANCE_UNKNOWN",
                operation_id=op.id,
                observation=job.observations,
            )
            return {"task": None}

    def blocked(self, identity, data):
        with self.db.transaction(write=True) as session:
            op, job, receipt = self.owned(session, identity, data)
            if receipt.state == "completed" or receipt.result is not None:
                return {}  # A lost local ACK cannot invalidate a persisted result.
            if receipt.state != "prepared":
                receipt.state = "unknown"
                job.observations = MAX_ATTEMPTS
            if job.status != "cancelled":
                job.status = "failed" if receipt.state == "prepared" else "needs_review"
                job.error_code = data.code
            job.updated_at = self.clock()
            record(session, job, "story.agent_blocked", self.clock(), data.code, operation_id=op.id)
            return {}

    def persist(self, operation_id):
        directory = self.db.path.parent / "story-artifacts"
        try:
            with FileLock(str(self.db.path.parent / f"story-{operation_id}.lock"), timeout=0):
                with self.db.transaction(write=True) as session:
                    op = session.get(StoryOperation, operation_id)
                    job, receipt = session.get(Job, op.job_id), session.get(OperationReceipt, op.id)
                    if receipt.state == "completed" or receipt.result is None:
                        return
                    if job.save_attempts >= MAX_ATTEMPTS or job.next_run_at > self.clock():
                        return
                    job.save_attempts += 1
                    content = receipt.result.encode()
                directory.mkdir(exist_ok=True)
                temporary = directory / f"{operation_id}.part"
                try:
                    with temporary.open("wb") as target:
                        target.write(content)
                        target.flush()
                        os.fsync(target.fileno())
                    os.replace(temporary, directory / f"{operation_id}.txt")
                finally:
                    temporary.unlink(missing_ok=True)
                with self.db.transaction(write=True) as session:
                    op = session.get(StoryOperation, operation_id)
                    job, receipt = session.get(Job, op.job_id), session.get(OperationReceipt, op.id)
                    receipt.state, receipt.updated_at = "completed", self.clock()
                    job.artifact, job.stage = f"story-artifacts/{operation_id}.txt", "done"
                    if job.status != "cancelled":
                        job.status, job.error_code = "completed", None
                    job.updated_at = self.clock()
                    record(session, job, "story.artifact_persisted", self.clock(), operation_id=op.id)
        except Timeout:
            return  # A concurrent owned writer will finish; never dispatch again.
        except OSError:
            with self.db.transaction(write=True) as session:
                op = session.get(StoryOperation, operation_id)
                job = session.get(Job, op.job_id)
                if job.status != "cancelled":
                    job.status = "failed" if job.save_attempts >= MAX_ATTEMPTS else "waiting"
                    job.error_code = "ARTIFACT_WRITE_FAILED"
                job.next_run_at = self.clock() + 2 ** max(1, job.save_attempts)
                record(
                    session,
                    job,
                    "story.artifact_failed",
                    self.clock(),
                    "ARTIFACT_WRITE_FAILED",
                    operation_id=op.id,
                )

    def maintain(self):
        now, saves = self.clock(), []
        with self.db.transaction(write=True) as session:
            for op in session.scalars(select(StoryOperation).join(Job).where(Job.status != "completed")):
                job, receipt = session.get(Job, op.job_id), session.get(OperationReceipt, op.id)
                if receipt.result is not None and receipt.state != "completed":
                    if job.save_attempts < MAX_ATTEMPTS and job.next_run_at <= now:
                        saves.append(op.id)
                    continue
                if job.status in {"cancelled", "failed"} or receipt.state == "completed":
                    continue
                if receipt.state == "unknown" and job.observations >= MAX_ATTEMPTS:
                    continue  # Preserve the exact blocking reason until explicit reconciliation.
                pair = session.get(Pairing, op.pair_id) if op.pair_id else None
                expired = op.lease_until <= now or not pair or pair.state != "paired"
                if not expired and now < op.deadline:
                    continue
                uncertain = receipt.state != "prepared"
                code = "SEND_ACCEPTANCE_UNKNOWN" if uncertain else "EXTENSION_DISCONNECTED"
                if now >= op.deadline and not uncertain:
                    code = "BROWSER_RETRY_EXHAUSTED"
                status = "needs_review" if uncertain else "failed" if now >= op.deadline else "waiting"
                if uncertain:
                    receipt.state = "unknown"
                elif pair and pair.state != "paired":
                    op.pair_id, op.connection_id, op.lease_until = None, None, 0
                if (job.status, job.error_code) != (status, code):
                    job.status, job.error_code, job.updated_at = status, code, now
                    record(session, job, "story.connection_wait", now, code, operation_id=op.id)
        for identifier in saves:
            self.persist(identifier)

    def command(self, job_id, action, trace):
        with self.db.transaction(write=True) as session:
            job = session.get(Job, job_id)
            op = session.scalar(select(StoryOperation).where(StoryOperation.job_id == job_id))
            if not job or not op:
                raise AppError("JOB_NOT_FOUND")
            receipt = session.get(OperationReceipt, op.id)
            if action == "cancel":
                if job.status != "completed":
                    job.status = "cancelled"
            elif action == "reconcile":
                if receipt.state in {"dispatching", "unknown", "accepted"}:
                    job.observations, op.deadline = 0, self.clock() + 900
                    if receipt.result is not None:
                        job.save_attempts, job.next_run_at = 0, self.clock()
            elif action == "resume":
                if receipt.state in {"dispatching", "unknown"}:
                    raise AppError("SEND_ACCEPTANCE_UNKNOWN")
                if job.status == "cancelled":
                    raise AppError("INVALID_TRANSITION")
                if job.status != "completed":
                    job.status, job.error_code = "waiting", None
                    job.save_attempts, job.next_run_at = 0, self.clock()
                    if receipt.state == "prepared":
                        job.attempts, op.deadline = 0, self.clock() + 900
            else:
                raise AppError("INVALID_TRANSITION")
            job.updated_at = self.clock()
            record(session, job, f"story.{action}", self.clock(), operation_id=op.id, command_trace_id=trace)
            return job_view(job, receipt)
