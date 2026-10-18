"""Shared provider output and typed provider failures."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

Probability = Annotated[float, Field(ge=0, le=1)]


class RiskAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_alignment_probability: Probability
    goal_alignment_confidence: Probability
    duplicate_obligation_probability: Probability
    duplicate_obligation_confidence: Probability
    counterparty_change_score: Probability
    counterparty_change_confidence: Probability
    missing_context_probability: Probability
    missing_context_confidence: Probability
    action_anomaly_score: Probability
    action_anomaly_confidence: Probability
    provider: str
    model_name: str
    latency_ms: float = Field(ge=0)
    schema_version: str = "1"
    outcome: Literal["success"] = "success"


class ProviderFailureCode(StrEnum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    MODEL_DISCOVERY_ERROR = "MODEL_DISCOVERY_ERROR"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class ProviderFailure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    code: ProviderFailureCode
    message: str
    retryable: bool
    latency_ms: float = Field(ge=0)
    model_name: str | None = None
    outcome: Literal["failure"] = "failure"


ProviderOutcome = Annotated[RiskAssessment | ProviderFailure, Field(discriminator="outcome")]
provider_outcome_adapter = TypeAdapter(ProviderOutcome)

