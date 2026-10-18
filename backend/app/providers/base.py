"""Provider-neutral decision interface."""

from typing import Protocol

from backend.app.models.risk import ProviderOutcome
from backend.app.models.state import AccountingState


class DecisionProvider(Protocol):
    async def evaluate(self, state: AccountingState) -> ProviderOutcome:
        """Return either a complete assessment or an explicit typed failure."""
        ...
