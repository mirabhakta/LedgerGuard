from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.graph.workflow import LedgerGuardWorkflow, create_sqlite_checkpointer
from backend.app.models import (
    AccountingState, ActionType, BusinessContext, ContextResponse, HistoricalAmountStats,
    HumanReviewResponse, ProposedAction, RiskAssessment,
)
from backend.app.models.risk import ProviderFailure, ProviderFailureCode
from backend.app.policy import PolicyEngine
from backend.app.tools import SimulatedExecutionTool


class Store:
    def records(self, company_id, record_type):
        return ()


class ContextBuilder:
    store = Store()

    def build(self, action):
        return AccountingState(
            proposed_action=action, candidate_matches=(),
            business_context=BusinessContext(
                company_id=action.company_id, vendor_transaction_count=0,
                historical_amount_stats=HistoricalAmountStats(observation_count=0),
            ), recent_ledger_history=(), deterministic_features={},
        )


class Provider:
    def __init__(self, **changes):
        self.changes = changes
        self.calls = 0

    async def evaluate(self, state):
        self.calls += 1
        values = {
            "goal_alignment_probability": 0.9, "goal_alignment_confidence": 0.9,
            "duplicate_obligation_probability": 0.1, "duplicate_obligation_confidence": 0.9,
            "counterparty_change_score": 0.1, "counterparty_change_confidence": 0.9,
            "missing_context_probability": 0.1, "missing_context_confidence": 0.9,
            "action_anomaly_score": 0.1, "action_anomaly_confidence": 0.9,
            "provider": "fake", "model_name": "fake-1", "latency_ms": 1,
        }
        values.update(self.changes)
        if self.changes.get("dynamic_missing"):
            values.pop("dynamic_missing")
            values["missing_context_probability"] = (
                0.9 if not state.proposed_action.vendor_id else 0.1
            )
        return RiskAssessment(**values)


class FailureProvider:
    async def evaluate(self, state):
        return ProviderFailure(
            provider="fake", code=ProviderFailureCode.TIMEOUT,
            message="timeout", retryable=True, latency_ms=1,
        )


def action(**changes):
    values = {
        "action_id": "a1", "action_type": ActionType.PAY_VENDOR_BILL,
        "company_id": "company-001", "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "amount": Decimal("100"), "currency": "USD", "vendor_id": "v1",
        "source_document_id": "b1", "agent_goal": "pay approved bill",
    }
    values.update(changes)
    return ProposedAction(**values)


@pytest.mark.asyncio
async def test_allow_routes_to_simulated_execution() -> None:
    provider = Provider()
    workflow = LedgerGuardWorkflow(ContextBuilder(), provider, PolicyEngine())
    result = await workflow.run(action(), thread_id="allow")
    assert result["status"] == "executed"
    assert result["execution_result"]["status"] == "SIMULATED"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_block_and_hard_precheck_never_execute() -> None:
    provider = Provider(duplicate_obligation_probability=0.99)
    workflow = LedgerGuardWorkflow(ContextBuilder(), provider, PolicyEngine())
    result = await workflow.run(action(), thread_id="blocked")
    assert result["status"] == "blocked" and result["execution_result"] is None
    hard_provider = Provider()
    hard = LedgerGuardWorkflow(ContextBuilder(), hard_provider, PolicyEngine())
    result = await hard.run(action(amount=Decimal("100001")), thread_id="hard")
    assert result["status"] == "blocked"
    assert hard_provider.calls == 0


@pytest.mark.asyncio
async def test_review_interrupt_approve_resume_and_stale_rejection() -> None:
    workflow = LedgerGuardWorkflow(
        ContextBuilder(), Provider(counterparty_change_score=0.9), PolicyEngine()
    )
    pending = await workflow.run(action(), thread_id="review")
    assert pending["__interrupt__"]
    decision = pending["policy_decision"]
    approved = HumanReviewResponse(
        approved=True, action_id="a1", assessment_hash=decision["assessment_hash"],
        reviewer="reviewer@example.com",
    )
    completed = await workflow.resume_review("review", approved)
    assert completed["status"] == "executed"

    stale_flow = LedgerGuardWorkflow(
        ContextBuilder(), Provider(counterparty_change_score=0.9), PolicyEngine()
    )
    pending = await stale_flow.run(action(action_id="a2"), thread_id="stale")
    stale = HumanReviewResponse(
        approved=True, action_id="wrong", assessment_hash=pending["policy_decision"]["assessment_hash"],
        reviewer="reviewer@example.com",
    )
    result = await stale_flow.resume_review("stale", stale)
    assert result["status"] == "blocked"
    assert result["error_state"]["code"] == "STALE_REVIEW_RESPONSE"


@pytest.mark.asyncio
async def test_context_interrupt_rebuilds_and_re_evaluates() -> None:
    provider = Provider(dynamic_missing=True)
    workflow = LedgerGuardWorkflow(ContextBuilder(), provider, PolicyEngine())
    pending = await workflow.run(
        action(
            action_type=ActionType.ADD_TRANSACTION, vendor_id=None,
            source_document_id=None,
        ),
        thread_id="context",
    )
    assert pending["__interrupt__"]
    response = ContextResponse(
        action_id="a1", updates={"vendor_id": "v1"}, supplied_by="operator",
        provenance="operator confirmed vendor from receipt",
    )
    completed = await workflow.resume_context("context", response)
    assert completed["status"] == "executed"
    assert completed["proposed_action"]["amount"] == "100"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_sqlite_checkpoint_contains_terminal_state(tmp_path) -> None:
    checkpointer = await create_sqlite_checkpointer(tmp_path / "workflow.sqlite3")
    workflow = LedgerGuardWorkflow(
        ContextBuilder(), Provider(), PolicyEngine(), checkpointer=checkpointer
    )
    await workflow.run(action(), thread_id="persisted")
    snapshot = await workflow.graph.aget_state(
        {"configurable": {"thread_id": "persisted"}}
    )
    assert snapshot.values["status"] == "executed"
    await checkpointer.conn.close()


@pytest.mark.asyncio
async def test_provider_failure_interrupts_for_review_and_reject_blocks() -> None:
    workflow = LedgerGuardWorkflow(ContextBuilder(), FailureProvider(), PolicyEngine())
    pending = await workflow.run(action(), thread_id="provider-failure")
    assert pending["__interrupt__"]
    decision = pending["policy_decision"]
    response = HumanReviewResponse(
        approved=False, action_id="a1", assessment_hash=decision["assessment_hash"],
        reviewer="reviewer@example.com",
    )
    result = await workflow.resume_review("provider-failure", response)
    assert result["status"] == "blocked"
    assert result["execution_result"] is None


@pytest.mark.asyncio
async def test_context_exception_and_schema_mismatch_never_execute() -> None:
    class BrokenContextBuilder(ContextBuilder):
        def build(self, action):
            raise RuntimeError("dataset unavailable")

    tool = SimulatedExecutionTool()
    workflow = LedgerGuardWorkflow(
        BrokenContextBuilder(), Provider(), PolicyEngine(), execution_tool=tool
    )
    result = await workflow.run(action(), thread_id="context-error")
    assert result["status"] == "blocked"
    assert result["error_state"]["code"] == "CONTEXT_BUILD_ERROR"
    assert tool.get("a1") is None

    with pytest.raises(ValueError, match="workflow state version"):
        await workflow.graph.ainvoke(
            {
                "proposed_action": action().model_dump(mode="json"),
                "workflow_version": "old", "audit_id": "audit", "status": "received",
            },
            {"configurable": {"thread_id": "old-version"}},
        )
