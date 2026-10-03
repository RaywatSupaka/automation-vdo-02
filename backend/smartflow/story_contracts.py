from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoryStart(Closed):
    draft_id: UUID
    expected_revision: int = Field(ge=1, strict=True)
    mode: Literal["simulation"]


class Sync(Closed):
    action: Literal["sync"]
    connection_id: UUID
    extension_version: str
    helper_version: str
    capability: Literal["story_simulator_v1"]


class OperationCommand(Closed):
    connection_id: UUID
    operation_id: UUID
    request_id: UUID
    lease_epoch: int = Field(ge=1, strict=True)


class Grant(OperationCommand):
    action: Literal["grant"]


class Result(OperationCommand):
    action: Literal["result"]
    result: str = Field(min_length=1, max_length=6000)


class Missing(OperationCommand):
    action: Literal["missing"]


class Blocked(OperationCommand):
    action: Literal["blocked"]
    code: Literal["EXTENSION_STORAGE_FAILED", "STORY_RESULT_INVALID"]


AgentCommand = Annotated[Sync | Grant | Result | Missing | Blocked, Field(discriminator="action")]


class WorkTask(OperationCommand):
    job_id: UUID
    revision_id: UUID
    trace_id: str
    lease_until: float
    mode: Literal["dispatch", "inspect"]
    simulation: Literal[True]
    topic: str = Field(max_length=2000)


class WorkReply(Closed):
    task: WorkTask | None = None
    granted: bool = False
    lease_until: float | None = None
    persisted: bool = False
    sha256: str | None = None


class StoryView(Closed):
    job_id: str
    revision_id: str
    draft_id: str
    draft_revision: int
    operation_id: str
    request_id: str
    receipt_state: str
    lease_epoch: int
    lease_until: float
    status: str
    error_code: str | None
    trace_id: str
    simulation: Literal[True] = True
    result: str | None = None
    sha256: str | None = None
