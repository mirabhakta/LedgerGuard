"""Provider-neutral accounting context."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .accounting import CanonicalAccountingRecord
from .action import ProposedAction


class CandidateMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    ledger_id: str
    source_id: str
    record_type: str
    date: date
    amount: Decimal | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    status: str | None = None
    match_score: float = Field(ge=0, le=1)
    match_reasons: tuple[str, ...]


class HistoricalAmountStats(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_count: int = Field(ge=0)
    mean: Decimal | None = None
    median: Decimal | None = None
    stddev: Decimal | None = None
    minimum: Decimal | None = None
    maximum: Decimal | None = None


class BusinessContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    business_type: str | None = None
    industry_naics: str | None = None
    current_account_id: str | None = None
    vendor_transaction_count: int = Field(ge=0)
    historical_amount_stats: HistoricalAmountStats
    category_history: tuple[str, ...] = ()
    account_history: tuple[str, ...] = ()
    previous_payment_destinations: tuple[str, ...] | None = None
    known_accounting_patterns: tuple[str, ...] = ()
    user_constraints: tuple[str, ...] = ()


class AccountingState(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposed_action: ProposedAction
    candidate_matches: tuple[CandidateMatch, ...]
    business_context: BusinessContext
    recent_ledger_history: tuple[CanonicalAccountingRecord, ...]
    deterministic_features: dict[str, Any]
    schema_version: str = "1"
    feature_version: str = "1"

    def inference_view(self) -> dict[str, Any]:
        return {
            "proposed_action": self.proposed_action.model_dump(mode="json"),
            "candidate_matches": [item.model_dump(mode="json") for item in self.candidate_matches],
            "business_context": self.business_context.model_dump(mode="json"),
            "recent_ledger_history": [item.inference_view() for item in self.recent_ledger_history],
            "deterministic_features": self.deterministic_features,
            "schema_version": self.schema_version,
            "feature_version": self.feature_version,
        }

