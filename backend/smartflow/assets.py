"""Bounded imports into application-owned storage. Never mutate original files."""

import hashlib
import os
import time
from pathlib import Path
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import BaseModel
from sqlalchemy import func, select

from smartflow.asset_models import DraftAsset
from smartflow.draft_contracts import REGISTRY
from smartflow.draft_models import DraftEvent
from smartflow.errors import AppError
from smartflow.observability import emit

MAX_FILE = 500 * 1024 * 1024
MAX_DRAFT = 2 * 1024 * 1024 * 1024


class AssetResponse(BaseModel):
    id: str
    field: str
    name: str
    size: int
    sha256: str | None
    missing: bool


def asset_path(db, asset_id):
    # IDs originate in DB; filenames and user paths never select storage locations.
    return db.path.parent / "draft-assets" / f"{asset_id}.bin"


def metadata(db, row):
    path = asset_path(db, row.id)
    missing = row.state != "ready" or not path.is_file() or path.stat().st_size != row.size
    return {
        "id": row.id,
        "field": row.field,
        "name": row.name,
        "size": row.size,
        "sha256": row.sha256,
        "missing": missing,
    }


def signature(extension, head):
    if extension == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    if extension in {".mp4", ".mov", ".m4v", ".m4a"}:
        return head[4:8] in {b"ftyp", b"moov", b"mdat"}
    if extension in {".mkv", ".webm"}:
        return head.startswith(b"\x1aE\xdf\xa3")
    if extension == ".avi":
        return head.startswith(b"RIFF") and head[8:12] == b"AVI "
    if extension == ".wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if extension in {".mp3", ".aac"}:
        return head.startswith(b"ID3") or (len(head) > 1 and head[0] == 255 and head[1] & 224 == 224)
    if extension == ".ogg":
        return head.startswith(b"OggS")
    if extension == ".ttf":
        return head.startswith((b"\x00\x01\x00\x00", b"true"))
    if extension == ".otf":
        return head.startswith(b"OTTO")
    return False


class Assets:
    def __init__(self, db, clock=time.time):
        from smartflow.drafts import Drafts

        self.db, self.clock, self.drafts = db, clock, Drafts(db, clock)

    def list(self, draft_id):
        with self.db.transaction() as session:
            self.drafts.owned(session, draft_id)
            return [
                metadata(self.db, row)
                for row in session.scalars(select(DraftAsset).where(DraftAsset.draft_id == draft_id))
            ]

    def verified_path(self, draft_id, asset_id):
        with self.db.transaction() as session:
            self.drafts.owned(session, draft_id)
            row = session.get(DraftAsset, asset_id)
            if not row or row.draft_id != draft_id:
                raise AppError("DRAFT_ASSET_INVALID")
            path = asset_path(self.db, row.id)
            if metadata(self.db, row)["missing"]:
                raise AppError("DRAFT_ASSET_MISSING")
            with path.open("rb") as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest()
            if actual != row.sha256:
                raise AppError("DRAFT_ASSET_INVALID")
            return path

    async def import_file(self, draft_id, field, name, size, key, stream, trace):
        spec = REGISTRY.get(field, {})
        extension = Path(name).suffix.lower()
        if (
            spec.get("kind") != "file"
            or extension not in spec["accept"].split(",")
            or not 0 < size <= MAX_FILE
            or len(name) > 200
            or any(ord(c) < 32 or c in "/\\:" for c in name)
        ):
            raise AppError("DRAFT_ASSET_INVALID")
        command_hash = hashlib.sha256(f"{draft_id}:{key}".encode()).hexdigest()
        with self.db.transaction(write=True) as session:
            draft = self.drafts.owned(session, draft_id)
            row = session.scalar(select(DraftAsset).where(DraftAsset.command_hash == command_hash))
            if row and (row.name, row.field, row.size) != (name, field, size):
                raise AppError("IDEMPOTENCY_CONFLICT")
            if not row:
                total, count = session.execute(
                    select(func.coalesce(func.sum(DraftAsset.size), 0), func.count()).where(
                        DraftAsset.draft_id == draft_id
                    )
                ).one()
                if total + size > MAX_DRAFT or count >= 200:
                    raise AppError("DRAFT_ASSET_QUOTA")
                row = DraftAsset(
                    id=str(uuid4()),
                    draft_id=draft_id,
                    command_hash=command_hash,
                    field=field,
                    name=name,
                    size=size,
                    state="pending",
                )
                session.add(row)
                session.flush()
                session.add(
                    DraftEvent(
                        draft_id=draft_id,
                        revision=draft.revision,
                        trace_id=trace,
                        name="draft.asset_reserved",
                        at=self.clock(),
                    )
                )
            asset_id = row.id
        directory = asset_path(self.db, asset_id).parent
        directory.mkdir(exist_ok=True)
        temporary = directory / f"{asset_id}-{uuid4().hex}.part"
        try:
            with FileLock(str(directory / f"{asset_id}.lock"), timeout=0):
                # The asset lock proves no live import owns these crash remnants.
                for remnant in directory.glob(f"{asset_id}-*.part"):
                    remnant.unlink()
                digest, count, head = hashlib.sha256(), 0, bytearray()
                with temporary.open("xb") as target:
                    async for chunk in stream:
                        count += len(chunk)
                        if count > size or count > MAX_FILE:
                            raise AppError("DRAFT_ASSET_INVALID")
                        head.extend(chunk[: max(0, 32 - len(head))])
                        digest.update(chunk)
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                if count != size or not signature(extension, bytes(head)):
                    raise AppError("DRAFT_ASSET_INVALID")
                with self.db.transaction(write=True) as session:
                    row = session.get(DraftAsset, asset_id)
                    checksum = digest.hexdigest()
                    if row.sha256 and row.sha256 != checksum:
                        raise AppError("IDEMPOTENCY_CONFLICT")
                    os.replace(temporary, asset_path(self.db, asset_id))
                    if row.state != "ready":
                        draft = self.drafts.owned(session, draft_id)
                        session.add(
                            DraftEvent(
                                draft_id=draft_id,
                                revision=draft.revision,
                                trace_id=trace,
                                name="draft.asset_saved",
                                at=self.clock(),
                            )
                        )
                    row.state, row.sha256 = "ready", checksum
                    result = metadata(self.db, row)
                emit(self.db.logger, "draft.asset_saved", draft_id=draft_id, trace_id=trace)
                return result
        except Timeout as exc:
            raise AppError("DRAFT_ASSET_BUSY") from exc
        except OSError as exc:
            raise AppError("DRAFT_SAVE_FAILED") from exc
        finally:
            # Only this request's temporary file; never source files or another import.
            temporary.unlink(missing_ok=True)
