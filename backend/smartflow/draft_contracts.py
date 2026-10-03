"""Versioned backend draft schema; incomplete fields are valid saved work."""

import json
import math
import re
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
    code: Literal["VALUE_OUT_OF_RANGE", "OPTION_INVALID", "DRAFT_ASSET_MISSING", "FIELD_REQUIRED"]


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


def active(spec, config):
    """A field's rules apply only while its controlling field has the registry's value (UI `when`)."""
    condition = spec.get("when")
    return condition is None or config.get(condition["field"]) == condition["equals"]


def blank(value):
    return not value if isinstance(value, list) else isinstance(value, str) and not value.strip()


# JavaScript StringToNumber grammar, ASCII digits only, so cross-field limits use the number the UI sees.
# Python float() differs: it accepts "1_0" and non-ASCII digits and rejects "0x8".
JS_SPACE = "\t\n\v\f\r    -     　﻿"
JS_TRIM = re.compile(f"^[{JS_SPACE}]+|[{JS_SPACE}]+$")
JS_DECIMAL = re.compile(r"[+-]?(?:(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|Infinity)", re.ASCII)
JS_RADIX = re.compile(r"0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)", re.ASCII)


def number(value):
    """`Number(value)` as the UI computes it (may be infinite); None where the UI gets NaN."""
    if not isinstance(value, str):
        return None
    text = JS_TRIM.sub("", value)
    if not text:
        return 0.0
    if JS_DECIMAL.fullmatch(text):
        return float(text)
    if JS_RADIX.fullmatch(text):
        try:
            return float(int(text, 0))
        except OverflowError:
            return math.inf
    return None


def completeness(config):
    """Required and cross-field rules from the registry; reported only, so incomplete drafts stay saveable.

    Single-value range and option checks stay in issues(); a field it already flags is not checked again.
    """
    flagged = {issue["field"] for issue in issues(config)}
    result = []
    for field, spec in REGISTRY.items():
        value = config.get(field, spec["initial"])
        if not active(spec, config):
            continue
        if spec.get("required") and blank(value):
            result.append({"field": field, "code": "FIELD_REQUIRED"})
            continue
        if field in flagged or blank(value):
            continue
        code = None
        if "maxLines" in spec:
            lines = [line for line in re.split(r"\r?\n", value) if line.strip()]
            if len(lines) > spec["maxLines"]:
                code = "VALUE_OUT_OF_RANGE"
        if "maxCountOf" in spec:
            count = number(value)
            if count is not None and count > len(config.get(spec["maxCountOf"]) or ()):
                code = "VALUE_OUT_OF_RANGE"
        if "optionsUpTo" in spec:
            source = spec["optionsUpTo"]
            # Mirrors the UI's `Math.max(0, Math.min(max, Number(source) || 0))` option count.
            limit = number(config.get(source["field"])) or 0
            limit = int(max(0, min(REGISTRY[source["field"]]["max"], limit)))
            if value not in source["fixed"] and value not in {str(n) for n in range(1, limit + 1)}:
                code = "OPTION_INVALID"
        if code:
            result.append({"field": field, "code": code})
    return result
