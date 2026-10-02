"""Mutable drafts are separate from jobs and immutable execution revisions."""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models import Base


class StoryDraft(Base):
    __tablename__ = "story_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_scope: Mapped[str] = mapped_column(String(40), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer)
    active_step: Mapped[int] = mapped_column(Integer)
    config: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[float] = mapped_column(Float)


class DraftCommand(Base):
    __tablename__ = "draft_commands"
    # Scope + client key hash; no untrusted key is written to logs.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("story_drafts.id"), index=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[str] = mapped_column(Text)


class DraftEvent(Base):
    __tablename__ = "draft_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("story_drafts.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    trace_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(40))
    at: Mapped[float] = mapped_column(Float)
