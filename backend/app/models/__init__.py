"""Stable domain contracts shared by LedgerGuard components."""

from .accounting import (
    AccountReference,
    CanonicalAccountingRecord,
    RawQuickBooksRecord,
    RecordType,
    SourceMetadata,
    StatusSource,
)
from .action import ActionType, ProposedAction, SyntheticDestinationMetadata
from .policy import FinalAction, PolicyDecision, PrecheckFact, PrecheckResult, TriggeredThreshold
from .risk import ProviderFailure, ProviderOutcome, RiskAssessment
from .scenario import Scenario, ScenarioType
from .state import (
    AccountingState,
    BusinessContext,
    CandidateMatch,
    HistoricalAmountStats,
)
from .workflow import ContextResponse, ExecutionResult, HumanReviewResponse

__all__ = [
    "AccountReference",
    "AccountingState",
    "ActionType",
    "BusinessContext",
    "CandidateMatch",
    "CanonicalAccountingRecord",
    "ContextResponse",
    "ExecutionResult",
    "FinalAction",
    "HistoricalAmountStats",
    "HumanReviewResponse",
    "PolicyDecision",
    "PrecheckFact",
    "PrecheckResult",
    "ProposedAction",
    "ProviderFailure",
    "ProviderOutcome",
    "RawQuickBooksRecord",
    "RecordType",
    "RiskAssessment",
    "Scenario",
    "ScenarioType",
    "SourceMetadata",
    "StatusSource",
    "SyntheticDestinationMetadata",
    "TriggeredThreshold",
]

