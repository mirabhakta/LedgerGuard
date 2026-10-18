from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.models import (
    ActionType, FinalAction, PrecheckResult, ProposedAction, ProviderFailure, RiskAssessment,
)
from backend.app.models.risk import ProviderFailureCode
from backend.app.policy import PolicyConfig, PolicyEngine


def action() -> ProposedAction:
    return ProposedAction(
        action_id="a1", action_type=ActionType.PAY_VENDOR_BILL, company_id="company-001",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc), amount=Decimal("100"),
        currency="USD", vendor_id="v1", source_document_id="b1", agent_goal="pay bill",
    )


def risk(**changes) -> RiskAssessment:
    values = {
        "goal_alignment_probability": 0.9, "goal_alignment_confidence": 0.9,
        "duplicate_obligation_probability": 0.1, "duplicate_obligation_confidence": 0.9,
        "counterparty_change_score": 0.1, "counterparty_change_confidence": 0.9,
        "missing_context_probability": 0.1, "missing_context_confidence": 0.9,
        "action_anomaly_score": 0.1, "action_anomaly_confidence": 0.9,
        "provider": "fake", "model_name": "fake-1", "latency_ms": 1,
    }
    values.update(changes)
    return RiskAssessment(**values)


def test_hard_violation_has_highest_priority() -> None:
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=True, reason_codes=("HARD",)),
        risk(missing_context_probability=1), audit_id="audit-1",
    )
    assert decision.final_action is FinalAction.BLOCK
    assert decision.reason_codes == ("HARD",)
    assert decision.audit_id == "audit-1"


@pytest.mark.parametrize(
    ("changes", "expected", "reason"),
    [
        ({"duplicate_obligation_probability": 0.85}, FinalAction.BLOCK, "DUPLICATE_RISK"),
        ({"goal_alignment_probability": 0.49}, FinalAction.REQUIRE_APPROVAL, "GOAL_MISMATCH"),
        ({"counterparty_change_score": 0.70}, FinalAction.REQUIRE_APPROVAL, "COUNTERPARTY_CHANGE_RISK"),
        ({"missing_context_probability": 0.70}, FinalAction.REQUEST_CONTEXT, "MISSING_CONTEXT"),
        ({"action_anomaly_score": 0.80}, FinalAction.REQUIRE_APPROVAL, "ACTION_ANOMALY"),
        # Score clears the line, but confidence does not, so the score is ignored.
        (
            {"missing_context_probability": 0.735, "missing_context_confidence": 0.19},
            FinalAction.ALLOW,
            "POLICY_ALLOW",
        ),
    ],
)
def test_threshold_boundaries(changes, expected, reason) -> None:
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False), risk(**changes)
    )
    assert decision.final_action is expected
    assert decision.reason_codes == (reason,)


def test_just_below_risk_thresholds_and_exact_minimum_confidence_allow() -> None:
    assessment = risk(
        duplicate_obligation_probability=0.849,
        goal_alignment_probability=0.50,
        counterparty_change_score=0.699,
        missing_context_probability=0.699,
        action_anomaly_score=0.799,
        goal_alignment_confidence=0.60,
    )
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False), assessment
    )
    assert decision.final_action is FinalAction.ALLOW
    assert len(decision.config_hash) == 64 and len(decision.assessment_hash or "") == 64


def test_jev_safe_bill_low_confidence_is_allowed() -> None:
    """Jev on a safe bill: missing-context 0.735 @ 0.19, other confidences under 0.60."""
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False),
        risk(
            goal_alignment_probability=0.9, goal_alignment_confidence=0.10,
            duplicate_obligation_probability=0.1, duplicate_obligation_confidence=0.35,
            counterparty_change_score=0.1, counterparty_change_confidence=0.35,
            missing_context_probability=0.735, missing_context_confidence=0.19,
            action_anomaly_score=0.1, action_anomaly_confidence=0.10,
        ),
    )
    assert decision.final_action is FinalAction.ALLOW
    assert decision.reason_codes == ("POLICY_ALLOW",)


def test_confident_score_still_fires_at_the_confidence_floor() -> None:
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False),
        risk(missing_context_probability=0.70, missing_context_confidence=0.60),
    )
    assert decision.final_action is FinalAction.REQUEST_CONTEXT
    assert decision.reason_codes == ("MISSING_CONTEXT",)


def test_duplicate_priority_beats_missing_context() -> None:
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False),
        risk(duplicate_obligation_probability=0.99, missing_context_probability=0.99),
    )
    assert decision.final_action is FinalAction.BLOCK


def test_provider_failures_never_allow() -> None:
    failure = ProviderFailure(
        provider="system_one", code=ProviderFailureCode.TIMEOUT,
        message="timeout", retryable=True, latency_ms=50,
    )
    decision = PolicyEngine().decide(
        action(), PrecheckResult(hard_violation=False), failure
    )
    assert decision.final_action is FinalAction.REQUIRE_APPROVAL
    assert decision.reason_codes == ("PROVIDER_TIMEOUT",)


@pytest.mark.parametrize("unsafe_fallback", [FinalAction.ALLOW, FinalAction.REQUEST_CONTEXT])
def test_provider_failure_fallback_configuration_cannot_authorize_or_loop(
    unsafe_fallback,
) -> None:
    with pytest.raises(ValidationError, match="must require approval or block"):
        PolicyConfig(provider_failure_fallback=unsafe_fallback)
