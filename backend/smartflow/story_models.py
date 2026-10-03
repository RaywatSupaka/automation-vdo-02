from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models import Base


class StoryRevision(Base):
    __tablename__ = "story_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("story_drafts.id"))
    draft_revision: Mapped[int] = mapped_column(Integer)
    config: Mapped[str] = mapped_column(Text)


class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    pair_id: Mapped[str] = mapped_column(ForeignKey("browser_pairings.id"), primary_key=True)
    connection_id: Mapped[str] = mapped_column(String(36))
    last_seen: Mapped[float] = mapped_column(Float)


class StoryOperation(Base):
    __tablename__ = "story_operations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("story_revisions.id"))
    pair_id: Mapped[str | None] = mapped_column(ForeignKey("browser_pairings.id"), nullable=True)
    connection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_epoch: Mapped[int] = mapped_column(Integer)
    lease_until: Mapped[float] = mapped_column(Float)
    deadline: Mapped[float] = mapped_column(Float)


class OperationReceipt(Base):
    __tablename__ = "operation_receipts"
    operation_id: Mapped[str] = mapped_column(ForeignKey("story_operations.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    state: Mapped[str] = mapped_column(String(24))
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[float] = mapped_column(Float)
