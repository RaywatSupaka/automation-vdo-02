from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request

from smartflow.auth import Permission, policy
from smartflow.contracts import error_responses
from smartflow.draft_contracts import (
    DraftAudit,
    DraftEventResponse,
    DraftInput,
    DraftResponse,
    DraftSummary,
    DraftUpdate,
)
from smartflow.drafts import Drafts

Key = Annotated[str, Header(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")]


def draft_router(db):
    router = APIRouter(prefix="/api", responses=error_responses(401, 403, 404, 409, 422, 500))
    drafts = Drafts(db)

    @router.post(
        "/story-drafts",
        status_code=201,
        response_model=DraftResponse,
        openapi_extra=policy(Permission.DRAFTS_WRITE),
    )
    def create(data: DraftInput, request: Request, idempotency_key: Key):
        return drafts.save(data, idempotency_key, request.state.trace_id)

    @router.get(
        "/story-drafts", response_model=list[DraftSummary], openapi_extra=policy(Permission.DRAFTS_READ)
    )
    def list_drafts(limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
        return drafts.list(limit, offset)

    @router.get(
        "/story-drafts/{draft_id}", response_model=DraftResponse, openapi_extra=policy(Permission.DRAFTS_READ)
    )
    def get(draft_id: UUID):
        return drafts.get(str(draft_id))

    @router.patch(
        "/story-drafts/{draft_id}",
        response_model=DraftResponse,
        openapi_extra=policy(Permission.DRAFTS_WRITE),
    )
    def update(draft_id: UUID, data: DraftUpdate, request: Request, idempotency_key: Key):
        return drafts.save(data, idempotency_key, request.state.trace_id, str(draft_id))

    @router.get(
        "/diagnostics/drafts",
        response_model=list[DraftAudit],
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
    def audit(limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
        return drafts.audit(limit, offset)

    @router.get(
        "/diagnostics/drafts/{draft_id}/events",
        response_model=list[DraftEventResponse],
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
    def events(
        draft_id: UUID,
        after: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ):
        return drafts.events(str(draft_id), after, limit)

    return router
