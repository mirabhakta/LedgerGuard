from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .action import FinalAction


class PrecheckResult(BaseModel):
    passed: bool = True
    hard_block: bool = False
    requires_review: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    deterministic_features: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    final_action: FinalAction
    reason_codes: list[str] = Field(default_factory=list)
    triggered_thresholds: list[str] = Field(default_factory=list)
    provider: str
    audit_id: str | None = None
    fail_safe_triggered: bool = False
