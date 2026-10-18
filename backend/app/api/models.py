"""Stable HTTP request and response contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import (
    ContextResponse,
    ExecutionResult,
    HumanReviewResponse,
    PolicyDecision,
    ProposedAction,
)


class DemoRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    provider: str = "rules"
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Literal["approve", "reject", "provide_context"]
    actor: str = Field(min_length=1)
    assessment_hash: str | None = None
    updates: dict[str, Any] | None = None
    provenance: str | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool = False
    audit_id: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    providers: tuple[str, ...]
    scenario_count: int = Field(ge=0)


class ContextSummaryResponse(BaseModel):
    candidate_matches: list[dict[str, Any]]
    business_context: dict[str, Any]
    deterministic_features: dict[str, Any]
    schema_version: str
    feature_version: str


class AuditEventResponse(BaseModel):
    event_id: int = Field(ge=1)
    action_id: str
    audit_id: str
    type: str
    created_at: datetime
    schema_version: str
    payload: dict[str, Any]


class ExecutionAuthorizationResponse(BaseModel):
    action_id: str
    audit_id: str
    authorization_type: Literal["POLICY_ALLOW", "HUMAN_APPROVAL"]
    assessment_hash: str | None
    actor: str | None
    created_at: datetime
    decision: PolicyDecision
    review: HumanReviewResponse | None


class ActionListItemResponse(BaseModel):
    action_id: str
    idempotency_key: str | None
    audit_id: str
    scenario_id: str | None
    provider: str
    created_at: datetime
    updated_at: datetime
    status: str
    final_action: str | None
    latency_ms: float | None
    action: ProposedAction
    reason_codes: list[str]


class ActionListResponse(BaseModel):
    items: list[ActionListItemResponse]
    limit: int
    offset: int
    count: int
    total: int


class ActionDetailResponse(ActionListItemResponse):
    context: ContextSummaryResponse | None
    provider_outcome: dict[str, Any] | None
    policy_decision: PolicyDecision | None
    human_response: HumanReviewResponse | ContextResponse | None
    execution_result: ExecutionResult | None
    execution_authorization: ExecutionAuthorizationResponse | None
    error_state: dict[str, Any] | None
    audit_events: list[AuditEventResponse]


class BenchmarkRunResponse(BaseModel):
    run_id: str | None
    created_at: datetime | None
    provider: str | None
    model_name: str | None
    sample_size: int | None
    metrics: dict[str, Any] | None
    measured_cost_usd: float | None
    dataset_name: str | None = None
    artifact_path: str | None = None
    methodology_note: str | None = None


class BenchmarksResponse(BaseModel):
    status: Literal["measured", "not_run"]
    runs: list[BenchmarkRunResponse]


class DashboardResponse(BaseModel):
    processed: int = Field(ge=0)
    counts: dict[str, int]
    median_provider_latency_ms: float | None
