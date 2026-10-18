"""Proposed financial action contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionType(StrEnum):
    PAY_VENDOR_BILL = "PAY_VENDOR_BILL"
    POST_TRANSACTION = "POST_TRANSACTION"
    MATCH_EXISTING = "MATCH_EXISTING"
    ADD_TRANSACTION = "ADD_TRANSACTION"


class SyntheticDestinationMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    previous_destination: str | None = None
    new_destination: str
    changed_at: datetime | None = None
    is_synthetic: bool = True
    modification_reason: str
    source_record_ids: tuple[str, ...]

    @model_validator(mode="after")
    def require_synthetic_marker(self) -> "SyntheticDestinationMetadata":
        if not self.is_synthetic:
            raise ValueError("destination metadata is unsupported by the source dataset")
        return self


class ProposedAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action_id: str
    action_type: ActionType
    company_id: str
    timestamp: datetime
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    vendor_id: str | None = None
    vendor_name: str | None = None
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    account_id: str | None = None
    source_document_id: str | None = None
    proposed_category: str | None = None
    agent_goal: str = Field(min_length=1)
    agent_reasoning_summary: str | None = None
    destination: SyntheticDestinationMetadata | None = None
    user_constraints: tuple[str, ...] = ()

