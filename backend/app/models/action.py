from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FinalAction(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUEST_CONTEXT = "REQUEST_CONTEXT"
    BLOCK = "BLOCK"


class ProposedAction(BaseModel):
    action_id: str
    action_type: str
    timestamp: datetime | None = None
    amount: float | None = None
    currency: str | None = None
    vendor: str | None = None
    counterparty: str | None = None
    destination_account: str | None = None
    source_document_id: str | None = None
    proposed_category: str | None = None
    agent_goal: str
    agent_reasoning_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
