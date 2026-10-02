from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from smartflow.models import Base


class DraftAsset(Base):
    __tablename__ = "draft_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("story_drafts.id"), index=True)
    command_hash: Mapped[str] = mapped_column(String(64), unique=True)
    field: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(20))
