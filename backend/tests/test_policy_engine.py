import pytest

from backend.app.models.action import FinalAction
from backend.app.models.policy import PrecheckResult
from backend.app.policy.config import PolicyConfig
from backend.app.policy.engine import PolicyEngine
from backend.app.providers.helpers import provider_error_assessment
from backend.tests.factories import make_assessment, make_state

engine = PolicyEngine()


def decide(assessment, precheck=None, config=None):
    return engine.decide(
        state=make_state(),
        assessment=assessment,
        precheck_result=precheck or PrecheckResult(),
        config=config or PolicyConfig(),
    )


def test_low_risk_allows():
    decision = decide(make_assessment())
    assert decision.final_action == FinalAction.ALLOW
    assert decision.reason_codes == ["LOW_RISK"]


def test_provider_error_fails_safe_to_approval():
    error = provider_error_assessment(model_name="x", latency_ms=1.0, error_code="TIMEOUT", error_message="t")
    decision = decide(error)
    assert decision.final_action == FinalAction.REQUIRE_APPROVAL
    assert decision.fail_safe_triggered


@pytest.mark.parametrize(
    ("signal", "expected", "threshold"),
    [
        ("goal_misalignment_risk", FinalAction.BLOCK, "goal_misalignment_block_threshold"),
        ("duplicate_obligation_risk", FinalAction.BLOCK, "duplicate_block_threshold"),
        ("counterparty_change_risk", FinalAction.REQUIRE_APPROVAL, "counterparty_review_threshold"),
        ("missing_context_risk", FinalAction.REQUEST_CONTEXT, "missing_context_threshold"),
        ("action_anomaly_risk", FinalAction.REQUIRE_APPROVAL, "anomaly_review_threshold"),
    ],
)
def test_each_threshold_triggers_and_is_recorded(signal, expected, threshold):
    decision = decide(make_assessment(**{signal: 0.95}))
    assert decision.final_action == expected
    assert decision.triggered_thresholds == [threshold]


def test_threshold_comes_from_config():
    assessment = make_assessment(duplicate_obligation_risk=0.86)
    assert decide(assessment).final_action == FinalAction.ALLOW
    assert decide(assessment, config=PolicyConfig(duplicate_block_threshold=0.85)).final_action == FinalAction.BLOCK


def test_low_confidence_requires_approval():
    decision = decide(make_assessment(confidence=0.3))
    assert decision.final_action == FinalAction.REQUIRE_APPROVAL
    assert decision.reason_codes == ["LOW_PROVIDER_CONFIDENCE"]


def test_precheck_hard_block_wins():
    decision = decide(make_assessment(), precheck=PrecheckResult(hard_block=True, reason_codes=["OVER_HARD_LIMIT"]))
    assert decision.final_action == FinalAction.BLOCK
    assert decision.reason_codes == ["OVER_HARD_LIMIT"]
