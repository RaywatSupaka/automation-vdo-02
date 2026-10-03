"""Authenticated local workspace draft persistence, independent of job dispatch."""

import hashlib
import json
import os
import shutil
import time
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select

from smartflow.draft_contracts import REGISTRY, DraftInput, DraftUpdate, completeness, issues
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


def response(row, missing=()):
    config = json.loads(row.config)
    # Value issues stay in draft_contracts.issues (job start uses it); completeness only reports, so an
    # incomplete draft still saves; file state is storage-owned.
    reported = [{"field": field, "code": "DRAFT_ASSET_MISSING"} for field in missing]
    return {**summary(row), "config": config, "issues": [*issues(config), *completeness(config), *reported]}


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

    def successor(self, source_id, key, trace_id):
        """Next draft after a job start: same settings, per-story content reset, setting files cloned.

        Idempotent per key: IDs derive from the command, so a lost ACK replays the same draft.
        Files are linked (or copied) before the write transaction; rows commit with the command.
        """
        from smartflow.asset_models import DraftAsset
        from smartflow.assets import asset_path, metadata

        command_id = digest([self.scope, "successor", key])
        input_hash = digest(["successor", source_id])
        with self.db.transaction() as session:
            previous = session.get(DraftCommand, command_id)
            if previous:
                if previous.input_hash != input_hash:
                    raise AppError("IDEMPOTENCY_CONFLICT")
                return json.loads(previous.response)
            source = self.owned(session, source_id)
            config = json.loads(source.config)
            carried = {}
            for field, spec in REGISTRY.items():
                if spec.get("perStory"):
                    config[field] = spec["initial"]
                elif spec["kind"] == "file":
                    ready = []
                    for asset_id in config[field]:
                        row = session.get(DraftAsset, asset_id)
                        if row and row.draft_id == source.id and not metadata(self.db, row)["missing"]:
                            ready.append((row.id, row.name, row.size, row.sha256))
                    carried[field] = ready
        draft_id = str(uuid5(NAMESPACE_URL, "smartflow:draft:" + command_id))
        clones = {}
        for field, rows in carried.items():
            clones[field] = []
            for old_id, name, size, sha in rows:
                new_id = str(uuid5(NAMESPACE_URL, f"smartflow:asset:{command_id}:{old_id}"))
                target = asset_path(self.db, new_id)
                if not target.is_file():
                    temporary = target.with_suffix(".clone")
                    temporary.unlink(missing_ok=True)
                    try:
                        os.link(asset_path(self.db, old_id), temporary)
                    except OSError:
                        shutil.copyfile(asset_path(self.db, old_id), temporary)
                    os.replace(temporary, target)
                clones[field].append((new_id, name, size, sha))
            config[field] = [row[0] for row in clones[field]]
        with self.db.transaction(write=True) as session:
            previous = session.get(DraftCommand, command_id)
            if previous:
                return json.loads(previous.response)
            now = self.clock()
            row = StoryDraft(
                id=draft_id,
                owner_scope=self.scope,
                revision=1,
                schema_version=1,
                active_step=0,
                config=encode(config),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            for field, rows in clones.items():
                for new_id, name, size, sha in rows:
                    session.add(
                        DraftAsset(
                            id=new_id,
                            draft_id=draft_id,
                            command_hash=digest(["clone", new_id]),
                            field=field,
                            name=name,
                            size=size,
                            sha256=sha,
                            state="ready",
                        )
                    )
            session.flush()
            result = response(row)
            session.add(
                DraftCommand(id=command_id, draft_id=draft_id, input_hash=input_hash, response=encode(result))
            )
            session.add(
                DraftEvent(
                    draft_id=draft_id, revision=1, trace_id=trace_id, name="draft.successor_created", at=now
                )
            )
        emit(self.db.logger, "draft.successor_created", draft_id=draft_id, revision=1, trace_id=trace_id)
        return result

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
            row = self.owned(session, draft_id)
            return response(row, self.missing(session, json.loads(row.config)))

    def missing(self, session, config):
        """Map each file field to its referenced ids whose stored bytes are no longer intact."""
        from smartflow.asset_models import DraftAsset
        from smartflow.assets import metadata

        result = {}
        for field, spec in REGISTRY.items():
            if spec["kind"] != "file":
                continue
            ids = set()
            for asset_id in config.get(field, ()):
                asset = session.get(DraftAsset, asset_id)
                if asset is None or metadata(self.db, asset)["missing"]:
                    ids.add(asset_id)
            if ids:
                result[field] = ids
        return result

    def checked_missing(self, session, row, config, previous):
        """Reject invalid references and newly referenced missing files; return the rest.

        A file the row already referenced can disappear from storage after it was saved.
        Rejecting it would block every later unrelated edit, so it is reported instead.
        """
        from smartflow.asset_models import DraftAsset

        for field, spec in REGISTRY.items():
            if spec["kind"] != "file":
                continue
            if len(set(config[field])) != len(config[field]):
                raise AppError("DRAFT_ASSET_INVALID")
            for asset_id in config[field]:
                asset = session.get(DraftAsset, asset_id)
                if not asset or asset.draft_id != row.id or asset.field != field:
                    raise AppError("DRAFT_ASSET_INVALID")
        missing = self.missing(session, config)
        if any(ids - set(previous.get(field, ())) for field, ids in missing.items()):
            raise AppError("DRAFT_ASSET_MISSING")
        return missing

    def save(self, data: DraftInput, key: str, trace_id: str, draft_id=None):
        payload = data.model_dump()
        config = payload["config"]
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
                previous = json.loads(row.config)
                row.revision += 1
            else:
                row = StoryDraft(id=str(uuid4()), owner_scope=self.scope, revision=1, created_at=self.clock())
                previous = {}
                session.add(row)
            row.schema_version, row.active_step = data.schema_version, data.active_step
            row.config, row.updated_at = encode(config), self.clock()
            missing = self.checked_missing(session, row, config, previous)
            session.flush()
            result = response(row, missing)
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
