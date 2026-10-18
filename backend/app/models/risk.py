from __future__ import annotations

from pydantic import BaseModel, Field


class RiskSignal(BaseModel):
    # value: 0.0 = low risk, 1.0 = high risk
    value: float = Field(ge=0.0, le=1.0)

    # confidence: 0.0 = uncertain, 1.0 = highly confident
    confidence: float = Field(ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    goal_misalignment_risk: RiskSignal
    duplicate_obligation_risk: RiskSignal
    counterparty_change_risk: RiskSignal
    missing_context_risk: RiskSignal
    action_anomaly_risk: RiskSignal

    model_name: str
    latency_ms: float = Field(ge=0.0)

    had_error: bool = False
    used_fallback: bool = False

    error_code: str | None = None
    error_message: str | None = None
