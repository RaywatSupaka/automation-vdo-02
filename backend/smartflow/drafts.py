"""Authenticated local workspace draft persistence, independent of job dispatch."""

import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import select

from smartflow.draft_contracts import REGISTRY, DraftInput, DraftUpdate, issues
from smartflow.draft_models import DraftCommand, DraftEvent, StoryDraft
from smartflow.errors import AppError
from smartflow.observability import emit


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def summary(row):
    return {
        key: getattr(row, key)
        for key in ("id", "revision", "schema_version", "active_step", "created_at", "updated_at")
    }


def response(row):
    config = json.loads(row.config)
    return {**summary(row), "config": config, "issues": issues(config)}


class Drafts:
    # Local sessions have no persistent account identity yet. Scope is the local
    # workspace, not a transient session token or a user-supplied owner field.
    def __init__(self, db, clock=time.time, scope="local-workspace"):
        self.db, self.clock, self.scope = db, clock, scope

    def owned(self, session, draft_id):
        row = session.get(StoryDraft, draft_id)
        if row is None or row.owner_scope != self.scope:
            raise AppError("DRAFT_NOT_FOUND")
        return row

    def list(self, limit=100, offset=0):
        with self.db.transaction() as session:
            return [
                summary(row)
                for row in session.scalars(
                    select(StoryDraft)
                    .where(StoryDraft.owner_scope == self.scope)
                    .order_by(StoryDraft.updated_at.desc(), StoryDraft.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]

    def get(self, draft_id):
        with self.db.transaction() as session:
            return response(self.owned(session, draft_id))

    def save(self, data: DraftInput, key: str, trace_id: str, draft_id=None):
        payload = data.model_dump()
        config = payload["config"]
        # Asset import is P2. Reject references that cannot yet be verified;
        # never acknowledge a browser File or arbitrary path as persisted media.
        if any(config[field] for field, spec in REGISTRY.items() if spec["kind"] == "file"):
            raise AppError("DRAFT_ASSET_UNAVAILABLE")
        command_id = digest([self.scope, key])
        input_hash = digest([draft_id, payload])
        with self.db.transaction(write=True) as session:
            previous = session.get(DraftCommand, command_id)
            if previous:
                if previous.input_hash != input_hash:
                    raise AppError("IDEMPOTENCY_CONFLICT")
                self.owned(session, previous.draft_id)
                return json.loads(previous.response)
            if draft_id:
                row = self.owned(session, draft_id)
                if not isinstance(data, DraftUpdate) or row.revision != data.expected_revision:
                    raise AppError("DRAFT_REVISION_CONFLICT")
                row.revision += 1
            else:
                row = StoryDraft(id=str(uuid4()), owner_scope=self.scope, revision=1, created_at=self.clock())
                session.add(row)
            row.schema_version, row.active_step = data.schema_version, data.active_step
            row.config, row.updated_at = encode(config), self.clock()
            session.flush()
            result = response(row)
            session.add(
                DraftCommand(id=command_id, draft_id=row.id, input_hash=input_hash, response=encode(result))
            )
            session.add(
                DraftEvent(
                    draft_id=row.id,
                    revision=row.revision,
                    trace_id=trace_id,
                    name="draft.saved",
                    at=row.updated_at,
                )
            )
        emit(
            self.db.logger,
            "draft.saved",
            draft_id=result["id"],
            revision=result["revision"],
            trace_id=trace_id,
        )
        return result

    def audit(self, limit=100, offset=0):
        return [
            {"draft_id": row["id"], **{k: row[k] for k in ("revision", "active_step", "updated_at")}}
            for row in self.list(limit, offset)
        ]

    def events(self, draft_id, after=0, limit=100):
        with self.db.transaction() as session:
            self.owned(session, draft_id)
            return [
                {key: getattr(row, key) for key in ("id", "draft_id", "revision", "trace_id", "name", "at")}
                for row in session.scalars(
                    select(DraftEvent)
                    .where(DraftEvent.draft_id == draft_id, DraftEvent.id > after)
                    .order_by(DraftEvent.id)
                    .limit(limit)
                )
            ]
