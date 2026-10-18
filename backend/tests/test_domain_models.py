from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.models.action import ActionType, ProposedAction, SyntheticDestinationMetadata
from backend.app.models.risk import RiskAssessment


def test_proposed_action_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError):
        ProposedAction(
            action_id="action-1",
            action_type=ActionType.PAY_VENDOR_BILL,
            company_id="company-001",
            timestamp=datetime.now(UTC),
            amount=Decimal("0.00"),
            currency="USD",
            agent_goal="Pay bills due today",
        )


def test_proposed_action_rejects_unknown_financial_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProposedAction(
            action_id="action-1",
            action_type=ActionType.PAY_VENDOR_BILL,
            company_id="company-001",
            timestamp=datetime.now(UTC),
            amount=Decimal("10.00"),
            currency="USD",
            agent_goal="Pay bills due today",
            ammount=Decimal("10.00"),
        )


def test_destination_requires_explicit_synthetic_marker() -> None:
    with pytest.raises(ValidationError):
        SyntheticDestinationMetadata(
            new_destination="bank-new",
            is_synthetic=False,
            modification_reason="Destination-change stress case",
            source_record_ids=("company-001:bill:bill-1",),
        )


def test_risk_probabilities_are_bounded() -> None:
    values = dict(
        goal_alignment_probability=1.1,
        goal_alignment_confidence=0.9,
        duplicate_obligation_probability=0.1,
        duplicate_obligation_confidence=0.9,
        counterparty_change_score=0.1,
        counterparty_change_confidence=0.9,
        missing_context_probability=0.1,
        missing_context_confidence=0.9,
        action_anomaly_score=0.1,
        action_anomaly_confidence=0.9,
        provider="test",
        model_name="test-model",
        latency_ms=1.0,
    )
    with pytest.raises(ValidationError):
        RiskAssessment(**values)

