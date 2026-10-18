from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .action import FinalAction, ProposedAction


class Scenario(BaseModel):
    scenario_id: str
    scenario_type: str
    proposed_action: ProposedAction
    source_record_ids: list[str] = Field(default_factory=list)
    original_data: dict[str, Any] = Field(default_factory=dict)
    modifications: dict[str, Any] = Field(default_factory=dict)
    modification_reason: str | None = None
    expected_action: FinalAction | None = None
    expected_risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
