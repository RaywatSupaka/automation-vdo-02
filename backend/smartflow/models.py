from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    command_key: Mapped[str] = mapped_column(String(80), unique=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(120))
    scenario: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), index=True)
    stage: Mapped[str] = mapped_column(String(24))
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(36))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    save_attempts: Mapped[int] = mapped_column(Integer, default=0)
    observations: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[float] = mapped_column(Float, default=0)
    artifact: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[float] = mapped_column(Float)


class Receipt(Base):
    __tablename__ = "receipts"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    state: Mapped[str] = mapped_column(String(24))
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[float] = mapped_column(Float)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    at: Mapped[float] = mapped_column(Float)
    name: Mapped[str] = mapped_column(String(60))
    stage: Mapped[str] = mapped_column(String(24))
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")


class SimulatedRequest(Base):
    """A durable external-system simulator, deliberately separate from receipts."""

    __tablename__ = "simulated_requests"
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    result: Mapped[str] = mapped_column(Text)
    sends: Mapped[int] = mapped_column(Integer, default=1)
