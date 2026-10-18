from backend.app.models import FinalAction, HumanReviewResponse, PrecheckResult
from backend.app.policy import PolicyEngine
from backend.app.tools import ExecutionDeniedError, SimulatedExecutionTool
from backend.tests.test_graph_workflow import action
from backend.tests.test_policy_engine import risk

import pytest


def test_direct_execution_rejects_non_authorized_decisions() -> None:
    item = action()
    decision = PolicyEngine().decide(
        item, PrecheckResult(hard_violation=False), risk(counterparty_change_score=0.9)
    )
    assert decision.final_action is FinalAction.REQUIRE_APPROVAL
    with pytest.raises(ExecutionDeniedError):
        SimulatedExecutionTool().execute(item, decision)


def test_review_must_reference_same_snapshot_and_execution_is_idempotent() -> None:
    item = action()
    decision = PolicyEngine().decide(
        item, PrecheckResult(hard_violation=False), risk(counterparty_change_score=0.9)
    )
    tool = SimulatedExecutionTool()
    wrong = HumanReviewResponse(
        approved=True, action_id=item.action_id, assessment_hash="wrong", reviewer="r"
    )
    with pytest.raises(ExecutionDeniedError):
        tool.execute(item, decision, human_review=wrong)
    review = wrong.model_copy(update={"assessment_hash": decision.assessment_hash})
    first = tool.execute(item, decision, human_review=review)
    second = tool.execute(item, decision, human_review=review)
    assert first.execution_id == second.execution_id
    assert second.idempotent_replay
