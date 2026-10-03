from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request

from smartflow.auth import Permission, policy
from smartflow.contracts import JobResponse, error_responses
from smartflow.story_contracts import AgentCommand, StoryStart, StoryView, WorkReply
from smartflow.story_workflow import StoryWorkflow


def story_router(db):
    service = StoryWorkflow(db)
    router = APIRouter(prefix="/api", responses=error_responses(401, 403, 404, 409, 422, 500))

    @router.post(
        "/stories", response_model=JobResponse, status_code=201, openapi_extra=policy(Permission.JOBS_CREATE)
    )
    def create(
        data: StoryStart,
        request: Request,
        idempotency_key: Annotated[str, Header(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")],
    ):
        return service.create(data, idempotency_key, request.state.trace_id)

    @router.get("/stories/{job_id}", response_model=StoryView, openapi_extra=policy(Permission.JOBS_READ))
    def detail(job_id: UUID):
        return service.detail(str(job_id))

    @router.get(
        "/diagnostics/stories/{job_id}",
        response_model=StoryView,
        response_model_exclude_none=True,
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
    def diagnostic(job_id: UUID):
        return service.detail(str(job_id), private=False)

    @router.post("/browser/work", response_model=WorkReply, openapi_extra=policy(Permission.BROWSER_WORK))
    def work(data: Annotated[AgentCommand, Body()], request: Request):
        return getattr(service, data.action)(request.state.principal, data)

    return router
