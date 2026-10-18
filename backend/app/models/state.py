from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from .action import ProposedAction


class CandidateMatch(BaseModel):
    record_id: str
    # Annotated as dt.date: a bare `date` annotation is shadowed by this field's own name.
    date: dt.date | None = None
    amount: float | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessContext(BaseModel):
    company_id: str | None = None
    business_type: str | None = None
    current_account: str | None = None
    vendor_history: dict[str, Any] = Field(default_factory=dict)
    historical_amount_stats: dict[str, float] = Field(default_factory=dict)
    known_payment_destinations: list[str] = Field(default_factory=list)
    known_accounting_patterns: list[str] = Field(default_factory=list)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccountingState(BaseModel):
    proposed_action: ProposedAction
    candidate_matches: list[CandidateMatch] = Field(default_factory=list)
    business_context: BusinessContext
    recent_ledger_history: list[dict[str, Any]] = Field(default_factory=list)
    deterministic_features: dict[str, Any] = Field(default_factory=dict)
    scenario_id: str | None = None
