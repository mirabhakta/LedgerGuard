"""Deterministic policy result contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FinalAction(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUEST_CONTEXT = "REQUEST_CONTEXT"
    BLOCK = "BLOCK"


class TriggeredThreshold(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    comparator: str
    threshold: float | str
    actual: float | str


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    final_action: FinalAction
    reason_codes: tuple[str, ...]
    triggered_thresholds: tuple[TriggeredThreshold, ...] = ()
    provider: str
    audit_id: str
    action_id: str
    config_version: str
    config_hash: str
    assessment_hash: str | None = None
    evaluated_rules: tuple[str, ...] = ()


class PrecheckFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    passed: bool
    detail: str


class PrecheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hard_violation: bool
    reason_codes: tuple[str, ...] = ()
    facts: tuple[PrecheckFact, ...] = ()
    schema_version: str = Field(default="1")

