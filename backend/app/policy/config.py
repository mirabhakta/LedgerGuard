"""Versioned, immutable policy configuration."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.action import ActionType
from backend.app.models.policy import FinalAction


class PolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = "1"
    absolute_amount_hard_limit: Decimal = Field(default=Decimal("100000.00"), gt=0)
    supported_currencies: frozenset[str] = frozenset({"USD"})
    supported_action_types: frozenset[ActionType] = frozenset(ActionType)
    duplicate_block_threshold: float = Field(default=0.85, ge=0, le=1)
    minimum_goal_alignment: float = Field(default=0.50, ge=0, le=1)
    counterparty_review_threshold: float = Field(default=0.70, ge=0, le=1)
    missing_context_threshold: float = Field(default=0.70, ge=0, le=1)
    anomaly_review_threshold: float = Field(default=0.80, ge=0, le=1)
    minimum_confidence: float = Field(default=0.60, ge=0, le=1)
    provider_failure_fallback: FinalAction = FinalAction.REQUIRE_APPROVAL

    @field_validator("provider_failure_fallback")
    @classmethod
    def provider_failure_must_not_authorize(
        cls, value: FinalAction
    ) -> FinalAction:
        if value not in {FinalAction.REQUIRE_APPROVAL, FinalAction.BLOCK}:
            raise ValueError("provider failure fallback must require approval or block")
        return value

    def stable_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(payload).hexdigest()
