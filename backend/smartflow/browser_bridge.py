"""One-time pairing and restricted agent identity. No job dispatch in this milestone."""

import hashlib
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.auth import Principal, Role
from smartflow.errors import AppError
from smartflow.models import Base
from smartflow.observability import emit

COMPAT = json.loads(Path(__file__).with_name("bridge_config.json").read_text())


def hashed(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Pairing(Base):
    __tablename__ = "browser_pairings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    extension_id: Mapped[str] = mapped_column(String(32))
    nonce_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    expires_at: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(20))
    last_seen: Mapped[float] = mapped_column(Float)


class BrowserEvent(Base):
    __tablename__ = "browser_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair_id: Mapped[str] = mapped_column(ForeignKey("browser_pairings.id"))
    name: Mapped[str] = mapped_column(String(40))
    trace_id: Mapped[str] = mapped_column(String(36))
    at: Mapped[float] = mapped_column(Float)


class PairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    extension_id: str = Field(pattern=r"^[a-p]{32}$")


class PairExchange(PairRequest):
    agent_token: str = Field(min_length=43, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    extension_version: str
    helper_version: str


class PairResponse(BaseModel):
    id: str
    extension_id: str
    state: str
    connected: bool
    last_seen: float


class PairCode(BaseModel):
    id: str
    code: str
    expires_at: float


class BridgeInfo(BaseModel):
    extension_id: str
    extension_version: str
    helper_version: str
    host_name: str
    pairings: list[PairResponse]


class Bridge:
    def __init__(self, db, mode, clock=time.time):
        self.db, self.mode, self.clock = db, mode, clock

    def record(self, session, row, name, trace):
        session.flush()
        session.add(BrowserEvent(pair_id=row.id, name=name, trace_id=trace, at=self.clock()))

    def describe(self, row):
        return {
            "id": row.id,
            "extension_id": row.extension_id,
            "state": row.state,
            "connected": row.state == "paired" and self.clock() - row.last_seen < 90,
            "last_seen": row.last_seen,
        }

    def info(self):
        with self.db.transaction() as session:
            rows = [
                self.describe(row)
                for row in session.scalars(select(Pairing).order_by(Pairing.expires_at.desc()).limit(20))
            ]
        return {
            **{k: COMPAT[k] for k in ("extension_id", "extension_version", "helper_version", "host_name")},
            "pairings": rows,
        }

    def create(self, data, trace):
        if data.extension_id != COMPAT["extension_id"]:
            raise AppError("EXTENSION_ID_MISMATCH")
        code = secrets.token_urlsafe(32)
        with self.db.transaction(write=True) as session:
            for old in session.scalars(select(Pairing).where(Pairing.state == "pending")):
                old.state = "revoked"
                self.record(session, old, "browser.revoked", trace)
            row = Pairing(
                id=str(uuid4()),
                extension_id=data.extension_id,
                nonce_hash=hashed(code),
                expires_at=self.clock() + 120,
                state="pending",
                last_seen=0,
            )
            session.add(row)
            self.record(session, row, "browser.pairing_requested", trace)
            result = {"id": row.id, "code": code, "expires_at": row.expires_at}
        emit(self.db.logger, "browser.pairing_requested", trace_id=trace)
        return result

    def authenticate(self, token):
        if not token:
            raise AppError("UNAUTHORIZED")
        fingerprint = hashed(token)
        with self.db.transaction() as session:
            row = session.scalar(select(Pairing).where(Pairing.token_hash == fingerprint))
            if row and row.state == "paired":
                return Principal(row.id, Role.BROWSER_AGENT, self.mode)
            row = session.scalar(select(Pairing).where(Pairing.nonce_hash == fingerprint))
            if row and row.state in {"pending", "paired"} and row.expires_at > self.clock():
                return Principal(row.id, Role.BROWSER_PAIRING, self.mode)
        raise AppError("UNAUTHORIZED")

    def exchange(self, identity, data, trace):
        if identity.role != Role.BROWSER_PAIRING:
            raise AppError("PERMISSION_DENIED")
        if (
            data.extension_version != COMPAT["extension_version"]
            or data.helper_version != COMPAT["helper_version"]
        ):
            raise AppError("EXTENSION_VERSION_MISMATCH")
        with self.db.transaction(write=True) as session:
            row = session.get(Pairing, identity.actor_id)
            if not row or row.state not in {"pending", "paired"} or row.expires_at <= self.clock():
                raise AppError("PAIRING_EXPIRED")
            if row.extension_id != data.extension_id:
                raise AppError("EXTENSION_ID_MISMATCH")
            fingerprint = hashed(data.agent_token)
            if row.token_hash and row.token_hash != fingerprint:
                raise AppError("PAIRING_ALREADY_USED")
            for old in session.scalars(
                select(Pairing).where(
                    Pairing.extension_id == row.extension_id, Pairing.state == "paired", Pairing.id != row.id
                )
            ):
                old.state = "revoked"
                self.record(session, old, "browser.revoked", trace)
            if row.state != "paired":
                self.record(session, row, "browser.paired", trace)
            row.token_hash, row.state, row.last_seen = fingerprint, "paired", self.clock()
            result = self.describe(row)
        emit(self.db.logger, "browser.paired", trace_id=trace)
        return result

    def status(self, identity):
        if identity.role != Role.BROWSER_AGENT:
            raise AppError("PERMISSION_DENIED")
        with self.db.transaction(write=True) as session:
            row = session.get(Pairing, identity.actor_id)
            if not row or row.state != "paired":
                raise AppError("UNAUTHORIZED")
            row.last_seen = self.clock()
            return self.describe(row)

    def revoke(self, pair_id, trace):
        with self.db.transaction(write=True) as session:
            row = session.get(Pairing, pair_id)
            if not row:
                raise AppError("PAIRING_NOT_FOUND")
            if row.state != "revoked":
                self.record(session, row, "browser.revoked", trace)
            row.state = "revoked"
            result = self.describe(row)
        emit(self.db.logger, "browser.revoked", trace_id=trace)
        return result
