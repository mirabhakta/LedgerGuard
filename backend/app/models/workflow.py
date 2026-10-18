"""Small, versioned workflow and simulated-execution contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HumanReviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    approved: bool
    action_id: str
    assessment_hash: str | None
    reviewer: str = Field(min_length=1)
    note: str | None = None


class ContextResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action_id: str
    updates: dict[str, Any]
    supplied_by: str = Field(min_length=1)
    provenance: str = Field(min_length=1)


class ExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str
    action_id: str
    audit_id: str
    status: str = "SIMULATED"
    executed_at: datetime
    idempotent_replay: bool = False
