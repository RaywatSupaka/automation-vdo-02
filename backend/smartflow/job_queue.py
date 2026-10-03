"""One read model for every kind of queued work, so the UI shows a single queue across features."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from smartflow.auth import Permission, policy
from smartflow.contracts import error_responses
from smartflow.models import Job
from smartflow.story_workflow import ACTIVE, operation_receipt, queue_positions

KINDS = {"story_simulated": "story"}  # Every other scenario is the simulator automation queue.


class QueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    kind: Literal["story", "automation"]
    title: str
    status: str
    stage: str
    error_code: str | None
    receipt_state: str | None
    queue_position: int | None  # Story FIFO only; 0 is the job the browser works on next.
    simulation: Literal[True] = True
    created_at: float
    updated_at: float


def queue_items(db, recent=20):
    """Unfinished work first (oldest first), then the most recently finished jobs."""
    with db.transaction() as session:
        positions = queue_positions(session)
        active = list(
            session.scalars(select(Job).where(Job.status.in_(ACTIVE)).order_by(Job.created_at, Job.id))
        )
        done = list(
            session.scalars(
                select(Job)
                .where(Job.status.not_in(ACTIVE))
                .order_by(Job.updated_at.desc(), Job.id)
                .limit(recent)
            )
        )
        items = []
        for job in [*active, *done]:
            receipt = operation_receipt(session, job)
            items.append(
                dict(
                    job_id=job.id,
                    kind=KINDS.get(job.scenario, "automation"),
                    title=job.title,
                    status=job.status,
                    stage=job.stage,
                    error_code=job.error_code,
                    receipt_state=receipt.state if receipt else None,
                    queue_position=positions.get(job.id),
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            )
        return items


def queue_router(db):
    router = APIRouter(prefix="/api", responses=error_responses(401, 403, 422, 500))

    @router.get("/queue", response_model=list[QueueItem], openapi_extra=policy(Permission.JOBS_READ))
    def queue(recent: Annotated[int, Query(ge=0, le=100)] = 20):
        return queue_items(db, recent)

    return router
