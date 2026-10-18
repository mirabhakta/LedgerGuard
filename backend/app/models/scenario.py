"""Traceable evaluation scenarios derived from sponsor records."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .action import ProposedAction
from .policy import FinalAction


class ScenarioType(StrEnum):
    SAFE_NORMAL_PAYMENT = "SAFE_NORMAL_PAYMENT"
    SEMANTIC_DUPLICATE = "SEMANTIC_DUPLICATE"
    PAYMENT_DESTINATION_CHANGE = "PAYMENT_DESTINATION_CHANGE"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    ACTION_GOAL_MISMATCH = "ACTION_GOAL_MISMATCH"
    HIGH_AMOUNT_BUT_PLAUSIBLE = "HIGH_AMOUNT_BUT_PLAUSIBLE"


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    source_company_id: str
    source_record_ids: tuple[str, ...]
    original_data: dict[str, Any]
    modifications: dict[str, Any]
    modification_reason: str
    synthetic_fields: tuple[str, ...] = ()
    proposed_action: ProposedAction
    expected_action: FinalAction
    expected_risk_flags: tuple[str, ...]
    schema_version: str = "1"

    def inference_action(self) -> ProposedAction:
        """Only the proposed action crosses into context/provider construction."""
        return self.proposed_action
