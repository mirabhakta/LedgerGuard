from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.models import (
    AccountingState, ActionType, BusinessContext, HistoricalAmountStats, ProposedAction,
    SyntheticDestinationMetadata,
)
from backend.app.providers.rules import RulesProvider


def _state(**action_changes):
    values = {
        "action_id": "a1", "action_type": ActionType.PAY_VENDOR_BILL,
        "company_id": "company-001", "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "amount": Decimal("100"), "currency": "USD", "vendor_id": "v1",
        "source_document_id": "b1", "agent_goal": "Pay approved bill",
    }
    values.update(action_changes)
    action = ProposedAction(**values)
    return AccountingState(
        proposed_action=action, candidate_matches=(),
        business_context=BusinessContext(
            company_id="company-001", vendor_transaction_count=0,
            historical_amount_stats=HistoricalAmountStats(observation_count=0),
        ), recent_ledger_history=(), deterministic_features={},
    )


@pytest.mark.asyncio
async def test_rules_provider_uses_shared_state_without_labels() -> None:
    outcome = await RulesProvider().evaluate(_state())
    assert outcome.provider == "rules"
    assert outcome.goal_alignment_probability == 0.9
    assert outcome.latency_ms >= 0


@pytest.mark.asyncio
async def test_rules_detect_goal_conflict_destination_change_and_missing_context() -> None:
    destination = SyntheticDestinationMetadata(
        previous_destination="old", new_destination="new", modification_reason="test",
        source_record_ids=("b1",),
    )
    conflict = await RulesProvider().evaluate(
        _state(agent_goal="Do not pay suppliers", destination=destination)
    )
    assert conflict.goal_alignment_probability < 0.1
    assert conflict.counterparty_change_score > 0.9
    missing = await RulesProvider().evaluate(
        _state(action_type=ActionType.ADD_TRANSACTION, vendor_id=None, source_document_id=None)
    )
    assert missing.missing_context_probability > 0.8
