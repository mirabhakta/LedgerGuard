"""Simulated execution that persists intent before creating an outcome."""

from datetime import datetime, timezone
from uuid import uuid4

from backend.app.db.repositories import AuditRepository
from backend.app.models.action import ProposedAction
from backend.app.models.policy import FinalAction, PolicyDecision
from backend.app.models.workflow import ExecutionResult, HumanReviewResponse

from .execution import ExecutionDeniedError


class PersistentSimulatedExecutionTool:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

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
                human_review and human_review.approved
                and human_review.action_id == action.action_id
                and human_review.assessment_hash == decision.assessment_hash
            )
        if not authorized:
            raise ExecutionDeniedError("action is not authorized")
        # Authorization is durable before an execution intent can be created. This
        # preserves the evidence even if the process fails immediately afterwards.
        self.repository.record_execution_authorization(
            decision,
            review=human_review if decision.final_action is FinalAction.REQUIRE_APPROVAL else None,
        )
        existing = self.repository.get_execution(action.action_id)
        if existing:
            return existing.model_copy(update={"idempotent_replay": True})
        execution_id = f"execution-{uuid4().hex}"
        if not self.repository.begin_execution(action.action_id, execution_id, decision.audit_id):
            existing = self.repository.get_execution(action.action_id)
            if existing:
                return existing.model_copy(update={"idempotent_replay": True})
            intent = self.repository.get_execution_intent(action.action_id)
            if intent is None or intent["audit_id"] != decision.audit_id:
                raise RuntimeError("execution is already in progress with conflicting evidence")
            # This tool has no external side effect: recovering the same persisted
            # simulated intent is safe and keeps its original execution identity.
            execution_id = intent["execution_id"]
        result = ExecutionResult(
            execution_id=execution_id, action_id=action.action_id,
            audit_id=decision.audit_id, executed_at=datetime.now(timezone.utc),
        )
        try:
            self.repository.complete_execution(result)
        except RuntimeError:
            existing = self.repository.get_execution(action.action_id)
            if existing:
                return existing.model_copy(update={"idempotent_replay": True})
            raise
        return result

    def get(self, action_id: str) -> ExecutionResult | None:
        return self.repository.get_execution(action_id)
