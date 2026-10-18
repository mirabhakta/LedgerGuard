"""Second-layer authorization guard for simulated financial execution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.app.models.action import ProposedAction
from backend.app.models.policy import FinalAction, PolicyDecision
from backend.app.models.workflow import ExecutionResult, HumanReviewResponse


class ExecutionDeniedError(RuntimeError):
    pass


class SimulatedExecutionTool:
    def __init__(self) -> None:
        self._executions: dict[str, ExecutionResult] = {}

    def execute(
        self,
        action: ProposedAction,
        decision: PolicyDecision,
        *,
        human_review: HumanReviewResponse | None = None,
    ) -> ExecutionResult:
        if decision.action_id != action.action_id:
            raise ExecutionDeniedError("policy decision references a different action")
        authorized = decision.final_action is FinalAction.ALLOW
        if decision.final_action is FinalAction.REQUIRE_APPROVAL:
            authorized = bool(
                human_review
                and human_review.approved
                and human_review.action_id == action.action_id
                and human_review.assessment_hash == decision.assessment_hash
            )
        if not authorized:
            raise ExecutionDeniedError(
                f"action is not authorized: {decision.final_action.value}"
            )
        existing = self._executions.get(action.action_id)
        if existing is not None:
            return existing.model_copy(update={"idempotent_replay": True})
        result = ExecutionResult(
            execution_id=f"execution-{uuid4().hex}", action_id=action.action_id,
            audit_id=decision.audit_id, executed_at=datetime.now(timezone.utc),
        )
        self._executions[action.action_id] = result
        return result

    def get(self, action_id: str) -> ExecutionResult | None:
        return self._executions.get(action_id)
