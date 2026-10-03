"""Public response contracts. Diagnostic projections never include user content."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from smartflow.auth import AuthMode, Permission, Role
from smartflow.jobs import Scenario

Status = Literal["queued", "running", "waiting", "failed", "needs_review", "cancelled", "completed"]
Stage = Literal["prepare", "generate", "save", "done"]
ReceiptState = Literal["prepared", "dispatching", "accepted", "completed", "unknown"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionResponse(Contract):
    actor_id: str
    role: Role
    auth_mode: AuthMode
    permissions: list[Permission]


class ErrorInfo(Contract):
    code: str
    message: str
    recovery: str
    http_status: int
    trace_id: str
    stage: Stage | None


class InvalidField(Contract):
    field: str
    type: str


class ErrorResponse(Contract):
    error: ErrorInfo
    fields: list[InvalidField] | None = None


class ReceiptInfo(Contract):
    state: ReceiptState
    request_id: str


class SafeJob(Contract):
    id: str
    status: Status
    stage: Stage
    trace_id: str
    attempts: int
    save_attempts: int
    observations: int
    created_at: float
    updated_at: float
    next_run_at: float
    provider: Literal["simulator"]
    simulation: Literal[True]
    error: ErrorInfo | None
    receipt: ReceiptInfo | None
    has_artifact: bool


class JobResponse(SafeJob):
    title: str
    scenario: Scenario | Literal["story_simulated"]


class StackFrame(Contract):
    file: str
    line: int
    function: str


class EventDetails(Contract):
    operation_id: str | None = None
    revision_id: str | None = None
    request_id: str | None = None
    lease_epoch: int | None = None
    attempt: int | None = None
    will_retry: bool | None = None
    observation: int | None = None
    result_found: bool | None = None
    exception_type: str | None = None
    frames: list[StackFrame] | None = None
    command_trace_id: str | None = None
    action: Literal["resume", "cancel", "reconcile"] | None = None
    outcome: Literal["applied", "noop"] | None = None


class EventResponse(Contract):
    id: int
    at: float
    name: str
    stage: Stage
    trace_id: str
    code: str | None
    details: EventDetails


class HealthResponse(Contract):
    version: str
    database: Literal["connected"]
    provider: Literal["simulator"]
    simulation: Literal[True]
    job_counts: dict[Status, int]
    events: int
    schema_revision: str
    mode: Literal["dev", "prod", "test"]
    worker_alive: bool


class NoActiveError(Contract):
    code: Literal["NO_ACTIVE_ERROR"]
    stage: Stage


class DiagnosticResponse(Contract):
    job: SafeJob
    events: list[EventResponse]
    events_total: int
    events_truncated: bool
    conclusion: ErrorInfo | NoActiveError


class ColumnInfo(Contract):
    name: str
    type: str
    nullable: bool


class TableInfo(Contract):
    name: str
    columns: list[ColumnInfo]


class DatabaseResponse(Contract):
    tables: list[TableInfo]


class JobRow(Contract):
    id: str
    status: Status
    stage: Stage
    error_code: str | None
    trace_id: str
    updated_at: float


class ReceiptRow(Contract):
    job_id: str
    request_id: str
    state: ReceiptState
    updated_at: float


class EventRow(Contract):
    id: int
    job_id: str
    trace_id: str
    at: float
    name: str
    stage: Stage
    code: str | None


class LogResponse(Contract):
    operation_id: str | None = None
    revision_id: str | None = None
    lease_epoch: int | None = None
    draft_id: str | None = None
    revision: int | None = None
    at: str
    level: str
    event: str
    actor_id: str | None = None
    role: Role | None = None
    auth_mode: AuthMode | None = None
    job_id: str | None = None
    trace_id: str | None = None
    command_trace_id: str | None = None
    request_id: str | None = None
    stage: str | None = None
    code: str | None = None
    status: str | int | None = None
    attempt: int | None = None
    event_id: int | None = None
    duration_ms: float | None = None
    method: str | None = None
    route: str | None = None
    frames: list[StackFrame] | None = None
    exception_type: str | None = None
    version: str | None = None


class OpenAPIDocument(BaseModel):
    # OpenAPI is extensible; application payloads above remain closed contracts.
    model_config = ConfigDict(extra="allow")
    openapi: str
    info: dict
    paths: dict
    components: dict = Field(default_factory=dict)


def error_responses(*codes: int):
    return {
        code: {
            "model": ErrorResponse,
            "description": {
                401: "UNAUTHORIZED",
                403: "ORIGIN_REJECTED or PERMISSION_DENIED",
                404: "JOB_NOT_FOUND or ROUTE_NOT_FOUND",
                405: "METHOD_NOT_ALLOWED",
                409: "Domain conflict; inspect error.code and recovery",
                422: "INPUT_INVALID; safe field locations only",
                500: "INTERNAL_ERROR; inspect trace",
            }[code],
            "headers": {"X-Trace-ID": {"schema": {"type": "string"}}},
        }
        for code in codes
    }
