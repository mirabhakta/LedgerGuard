"""LangGraph orchestration with interrupt/resume and guarded execution."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import uuid4

import aiosqlite
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.app.models.action import ProposedAction
from backend.app.models.accounting import RecordType
from backend.app.models.policy import PolicyDecision, PrecheckResult
from backend.app.models.risk import provider_outcome_adapter
from backend.app.models.state import AccountingState
from backend.app.models.workflow import ContextResponse, HumanReviewResponse
from backend.app.policy import PolicyEngine, run_prechecks
from backend.app.providers.base import DecisionProvider
from backend.app.services.context_builder import ContextBuilder
from backend.app.tools.execution import ExecutionDeniedError, SimulatedExecutionTool

from .routing import route_after_context, route_after_policy, route_after_precheck
from .state import AgentGraphState


WORKFLOW_VERSION = "1"
CONTEXT_UPDATE_FIELDS = frozenset(
    {
        "vendor_id", "vendor_name", "counterparty_id", "counterparty_name",
        "source_document_id", "proposed_category", "user_constraints",
        "agent_reasoning_summary",
    }
)


class LedgerGuardWorkflow:
    def __init__(
        self,
        context_builder: ContextBuilder,
        provider: DecisionProvider,
        policy: PolicyEngine,
        *,
        execution_tool: SimulatedExecutionTool | None = None,
        checkpointer: Any | None = None,
        event_sink: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.context_builder = context_builder
        self.provider = provider
        self.policy = policy
        self.execution_tool = execution_tool or SimulatedExecutionTool()
        self.checkpointer = checkpointer or InMemorySaver()
        self.event_sink = event_sink
        self.graph = self._compile()

    def _compile(self):
        builder = StateGraph(AgentGraphState)
        builder.add_node("plan_action", self._plan_action)
        builder.add_node("build_context", self._build_context)
        builder.add_node("hard_precheck", self._hard_precheck)
        builder.add_node("evaluate_risk", self._evaluate_risk)
        builder.add_node("policy_decide", self._policy_decide)
        builder.add_node(
            "human_review", self._human_review,
            destinations=("execute_action", "blocked_terminal"),
        )
        builder.add_node(
            "request_context", self._request_context,
            destinations=("build_context", "blocked_terminal"),
        )
        builder.add_node("execute_action", self._execute_action)
        builder.add_node("blocked_terminal", self._blocked_terminal)
        builder.add_edge(START, "plan_action")
        builder.add_edge("plan_action", "build_context")
        builder.add_conditional_edges("build_context", route_after_context)
        builder.add_conditional_edges("hard_precheck", route_after_precheck)
        builder.add_edge("evaluate_risk", "policy_decide")
        builder.add_conditional_edges("policy_decide", route_after_policy)
        builder.add_edge("execute_action", END)
        builder.add_edge("blocked_terminal", END)
        return builder.compile(checkpointer=self.checkpointer)

    async def run(
        self,
        action: ProposedAction,
        *,
        thread_id: str,
        scenario_id: str | None = None,
        audit_id: str | None = None,
    ) -> AgentGraphState:
        initial: AgentGraphState = {
            "user_goal": action.agent_goal,
            "proposed_action": action.model_dump(mode="json"),
            "accounting_state": None, "precheck_result": None,
            "provider_outcome": None, "policy_decision": None,
            "human_response": None, "execution_result": None,
            "audit_id": audit_id or f"audit-{uuid4().hex}", "current_scenario": scenario_id,
            "error_state": None, "status": "received",
            "workflow_version": WORKFLOW_VERSION,
        }
        return await self.graph.ainvoke(initial, self._config(thread_id))

    async def resume_review(
        self, thread_id: str, response: HumanReviewResponse
    ) -> AgentGraphState:
        return await self.graph.ainvoke(
            Command(resume=response.model_dump(mode="json")), self._config(thread_id)
        )

    async def resume_context(
        self, thread_id: str, response: ContextResponse
    ) -> AgentGraphState:
        return await self.graph.ainvoke(
            Command(resume=response.model_dump(mode="json")), self._config(thread_id)
        )

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        if not thread_id:
            raise ValueError("thread_id is required")
        return {"configurable": {"thread_id": thread_id}}

    def _plan_action(self, state: AgentGraphState) -> dict[str, Any]:
        _require_version(state)
        action = ProposedAction.model_validate(state["proposed_action"])
        return {"proposed_action": action.model_dump(mode="json"), "status": "planned"}

    async def _build_context(
        self, state: AgentGraphState
    ) -> dict[str, Any]:
        _require_version(state)
        try:
            accounting_state = self.context_builder.build(
                ProposedAction.model_validate(state["proposed_action"])
            )
        except Exception as exc:
            return {
                "error_state": {"code": "CONTEXT_BUILD_ERROR", "message": str(exc)},
                "status": "error",
            }
        return {
            "accounting_state": accounting_state.model_dump(mode="json"),
            "provider_outcome": None, "policy_decision": None,
            "status": "context_built",
        }

    async def _hard_precheck(self, state: AgentGraphState) -> dict[str, Any]:
        _require_version(state)
        action = ProposedAction.model_validate(state["proposed_action"])
        accounting_state = AccountingState.model_validate(state["accounting_state"])
        account_ids = frozenset(
            record.source_id
            for record in self.context_builder.store.records(
                action.company_id, RecordType.ACCOUNT,
            )
        )
        result = run_prechecks(
            action, accounting_state, self.policy.config, known_account_ids=account_ids
        )
        await self._emit("precheck_complete", {"hard_violation": result.hard_violation})
        return {"precheck_result": result.model_dump(mode="json"), "status": "prechecked"}

    async def _evaluate_risk(self, state: AgentGraphState) -> dict[str, Any]:
        _require_version(state)
        await self._emit("provider_started", {})
        outcome = await self.provider.evaluate(
            AccountingState.model_validate(state["accounting_state"])
        )
        await self._emit("risk_assessment_ready", {"outcome": outcome.outcome})
        return {"provider_outcome": outcome.model_dump(mode="json"), "status": "evaluated"}

    async def _policy_decide(self, state: AgentGraphState) -> dict[str, Any]:
        _require_version(state)
        raw_outcome = state.get("provider_outcome")
        outcome = provider_outcome_adapter.validate_python(raw_outcome) if raw_outcome else None
        decision = self.policy.decide(
            ProposedAction.model_validate(state["proposed_action"]),
            PrecheckResult.model_validate(state["precheck_result"]), outcome,
            audit_id=state["audit_id"],
        )
        await self._emit(
            "policy_decision",
            {
                "final_action": decision.final_action.value,
                "reason_codes": list(decision.reason_codes),
            },
        )
        if decision.final_action.value == "REQUIRE_APPROVAL":
            await self._emit("review_required", {"status": "decided"})
        elif decision.final_action.value == "REQUEST_CONTEXT":
            await self._emit("context_requested", {"status": "decided"})
        return {"policy_decision": decision.model_dump(mode="json"), "status": "decided"}

    def _human_review(
        self, state: AgentGraphState
    ) -> Command[Literal["execute_action", "blocked_terminal"]]:
        _require_version(state)
        decision = PolicyDecision.model_validate(state["policy_decision"])
        raw = interrupt(
            {
                "type": "human_review", "action_id": decision.action_id,
                "audit_id": decision.audit_id, "assessment_hash": decision.assessment_hash,
                "reason_codes": list(decision.reason_codes),
            },
            response_schema=HumanReviewResponse,
        )
        response = raw if isinstance(raw, HumanReviewResponse) else HumanReviewResponse.model_validate(raw)
        valid = (
            response.action_id == decision.action_id
            and response.assessment_hash == decision.assessment_hash
        )
        if not valid or not response.approved:
            return Command(
                update={
                    "human_response": response.model_dump(mode="json"),
                    "error_state": None if valid else {"code": "STALE_REVIEW_RESPONSE"},
                    "status": "review_rejected" if valid else "error",
                },
                goto="blocked_terminal",
            )
        return Command(
            update={"human_response": response.model_dump(mode="json"), "status": "approved"},
            goto="execute_action",
        )

    def _request_context(
        self, state: AgentGraphState
    ) -> Command[Literal["build_context", "blocked_terminal"]]:
        _require_version(state)
        action = ProposedAction.model_validate(state["proposed_action"])
        raw = interrupt(
            {
                "type": "context_request", "action_id": action.action_id,
                "allowed_fields": sorted(CONTEXT_UPDATE_FIELDS),
            },
            response_schema=ContextResponse,
        )
        response = raw if isinstance(raw, ContextResponse) else ContextResponse.model_validate(raw)
        if response.action_id != action.action_id or not set(response.updates) <= CONTEXT_UPDATE_FIELDS:
            return Command(
                update={"error_state": {"code": "INVALID_CONTEXT_RESPONSE"}, "status": "error"},
                goto="blocked_terminal",
            )
        updated = action.model_copy(update=response.updates)
        return Command(
            update={
                "proposed_action": updated.model_dump(mode="json"),
                "human_response": response.model_dump(mode="json"),
                "status": "context_supplied",
            },
            goto="build_context",
        )

    async def _execute_action(self, state: AgentGraphState) -> dict[str, Any]:
        _require_version(state)
        raw_human = state.get("human_response")
        review = (
            HumanReviewResponse.model_validate(raw_human)
            if isinstance(raw_human, dict) and "approved" in raw_human
            else None
        )
        try:
            result = self.execution_tool.execute(
                ProposedAction.model_validate(state["proposed_action"]),
                PolicyDecision.model_validate(state["policy_decision"]),
                human_review=review,
            )
        except ExecutionDeniedError as exc:
            await self._emit("action_blocked", {"status": "blocked"})
            return {
                "error_state": {"code": "EXECUTION_DENIED", "message": str(exc)},
                "status": "blocked", "execution_result": None,
            }
        await self._emit("execution_simulated", {"status": "executed"})
        return {"execution_result": result.model_dump(mode="json"), "status": "executed"}

    async def _blocked_terminal(self, state: AgentGraphState) -> dict[str, Any]:
        await self._emit("action_blocked", {"status": "blocked"})
        return {"execution_result": None, "status": "blocked"}

    async def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_sink is not None:
            await self.event_sink(event_type, payload)


async def create_sqlite_checkpointer(path: Path) -> AsyncSqliteSaver:
    connection = await aiosqlite.connect(path)
    checkpointer = AsyncSqliteSaver(connection)
    await checkpointer.setup()
    return checkpointer


def _require_version(state: AgentGraphState) -> None:
    if state.get("workflow_version") != WORKFLOW_VERSION:
        raise ValueError("unsupported or missing workflow state version")
