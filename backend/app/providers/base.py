from __future__ import annotations

from typing import Protocol

from backend.app.models.risk import RiskAssessment
from backend.app.models.state import AccountingState


class DecisionProvider(Protocol):
    async def evaluate(
        self,
        state: AccountingState,
    ) -> RiskAssessment:
        ...
