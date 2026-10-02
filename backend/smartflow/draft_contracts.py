"""Versioned backend draft schema; incomplete fields are valid saved work."""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, create_model, field_validator

REGISTRY = json.loads(Path(__file__).with_name("draft_fields.json").read_text(encoding="utf-8"))


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def draft_field(spec):
    if spec["kind"] == "checkbox":
        return StrictBool, spec["initial"]
    if spec["kind"] == "file":
        return list[Annotated[str, Field(pattern=r"^[a-f0-9-]{36}$")]], Field(
            default_factory=list, max_length=spec["maxFiles"]
        )
    return StrictStr, Field(default=spec["initial"], max_length=spec["maxLength"])


# This registry is a backend-owned contract. UI parity tests detect fields added
# without updating persistence; no runtime dependency on frontend source.
DraftConfig = create_model(
    "DraftConfig", __base__=ClosedModel, **{k: draft_field(v) for k, v in REGISTRY.items()}
)


class DraftInput(ClosedModel):
    schema_version: Literal[1] = 1
    active_step: int = Field(default=0, ge=0, le=4)
    config: DraftConfig = Field(default_factory=DraftConfig)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("integer version required")
        return value


class DraftUpdate(DraftInput):
    expected_revision: int = Field(ge=1)


class DraftIssue(ClosedModel):
    field: str
    code: Literal["VALUE_OUT_OF_RANGE", "OPTION_INVALID"]


class DraftSummary(ClosedModel):
    id: str
    revision: int
    schema_version: int
    active_step: int
    created_at: float
    updated_at: float


class DraftResponse(DraftSummary):
    config: DraftConfig
    issues: list[DraftIssue]


class DraftAudit(ClosedModel):
    draft_id: str
    revision: int
    active_step: int
    updated_at: float


class DraftEventResponse(ClosedModel):
    id: int
    draft_id: str
    revision: int
    trace_id: str
    name: str
    at: float


def issues(config):
    result = []
    for field, value in config.items():
        spec = REGISTRY[field]
        if not value:  # Empty inputs must remain saveable.
            continue
        code = None
        if "options" in spec and value not in spec["options"]:
            code = "OPTION_INVALID"
        if "min" in spec:
            try:
                number = float(value)
                quotient = number / spec.get("step", 1)
                if not spec["min"] <= number <= spec["max"] or abs(quotient - round(quotient)) > 1e-6:
                    code = "VALUE_OUT_OF_RANGE"
            except (ValueError, OverflowError):
                code = "VALUE_OUT_OF_RANGE"
        if code:
            result.append({"field": field, "code": code})
    return result
