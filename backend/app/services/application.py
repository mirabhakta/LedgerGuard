"""Application boundary joining scenarios, graph, audit persistence, and events."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.db.repositories import AuditRepository, IdempotencyConflictError
from backend.app.graph.workflow import LedgerGuardWorkflow, create_sqlite_checkpointer
from backend.app.models import AccountingState, ContextResponse, HumanReviewResponse
from backend.app.policy import PolicyEngine
from backend.app.providers.registry import ProviderRegistry
from backend.app.services.context_builder import ContextBuilder
from backend.app.services.scenario_loader import load_scenarios
from backend.app.tools.persistent_execution import PersistentSimulatedExecutionTool

from .event_bus import EventBus


class ApplicationError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class LedgerGuardApplication:
    def __init__(
        self,
        repository: AuditRepository,
        context_builder: ContextBuilder,
        providers: ProviderRegistry,
        policy: PolicyEngine,
        *,
        scenarios_path: Path,
        benchmark_dir: Path,
        event_bus: EventBus | None = None,
        checkpoint_path: Path | None = None,
    ) -> None:
        self.repository = repository
        self.context_builder = context_builder
        self.providers = providers
        self.policy = policy
        self.scenarios = {item.scenario_id: item for item in load_scenarios(scenarios_path)}
        self.benchmark_dir = benchmark_dir
        self.event_bus = event_bus or EventBus()
        self.checkpoint_path = checkpoint_path
        self._checkpointer: Any | None = None
        self._checkpoint_lock = asyncio.Lock()
        self._workflows: dict[str, LedgerGuardWorkflow] = {}
        self._resolution_locks: dict[str, asyncio.Lock] = {}

    async def run_demo(
        self, scenario_id: str, provider_name: str, *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        try:
            scenario = self.scenarios[scenario_id]
        except KeyError as exc:
            raise ApplicationError("SCENARIO_NOT_FOUND", "unknown scenario", 404) from exc
        try:
            provider = self.providers.get(provider_name)
        except KeyError as exc:
            raise ApplicationError("PROVIDER_NOT_FOUND", "unknown provider", 404) from exc
        action = scenario.inference_action().model_copy(
            update={"action_id": f"action-{uuid4().hex}"}
        )
        audit_id = f"audit-{uuid4().hex}"
        try:
            persisted_id = self.repository.create_received(
                action, audit_id=audit_id, provider=provider_name,
                scenario_id=scenario_id, idempotency_key=idempotency_key,
            )
        except IdempotencyConflictError as exc:
            raise ApplicationError(
                "IDEMPOTENCY_KEY_CONFLICT",
                "idempotency key was already used for a different request",
                409,
            ) from exc
        if persisted_id != action.action_id:
            return self.get_action(persisted_id)
        await self._event(action.action_id, audit_id, "action_received", {"scenario_id": scenario_id})
        workflow = await self._new_workflow(provider, action.action_id, audit_id)
        self._workflows[action.action_id] = workflow
        try:
            state = await workflow.run(
                action, thread_id=action.action_id, scenario_id=scenario_id, audit_id=audit_id
            )
            self.repository.save_workflow_state(action.action_id, state)
        except Exception as exc:
            # The received action remains durable and no unpersisted execution is authorized.
            await self._event(
                action.action_id, audit_id, "action_blocked",
                {"code": "WORKFLOW_ERROR", "message": str(exc)},
            )
            raise ApplicationError("WORKFLOW_ERROR", "workflow failed safely", 500) from exc
        return self.get_action(action.action_id)

    async def resolve(
        self,
        action_id: str,
        *,
        resolution: str,
        actor: str,
        assessment_hash: str | None = None,
        updates: dict[str, Any] | None = None,
        provenance: str | None = None,
    ) -> dict[str, Any]:
        row = self.repository.get_action(action_id)
        if row is None:
            raise ApplicationError("ACTION_NOT_FOUND", "action not found", 404)
        lock = self._resolution_locks.setdefault(action_id, asyncio.Lock())
        async with lock:
            # Re-read inside the lock so concurrent duplicate submissions cannot both resume.
            row = self.repository.get_action(action_id)
            if row is None:
                raise ApplicationError("ACTION_NOT_FOUND", "action not found", 404)
            state = row["state"] or {}
            decision = state.get("policy_decision") or {}
            if state.get("status") in {"executed", "blocked"} or state.get("execution_result"):
                raise ApplicationError(
                    "INVALID_STATE_TRANSITION", "action resolution is already terminal", 409
                )
            workflow = self._workflows.get(action_id)
            if workflow is None:
                if self.checkpoint_path is None:
                    raise ApplicationError(
                        "WORKFLOW_NOT_RESUMABLE", "workflow checkpoint is not active", 409
                    )
                try:
                    provider = self.providers.get(row["provider"])
                except KeyError as exc:
                    raise ApplicationError(
                        "PROVIDER_NOT_FOUND", "workflow provider is unavailable", 409
                    ) from exc
                workflow = await self._new_workflow(provider, action_id, row["audit_id"])
                self._workflows[action_id] = workflow
            if resolution in {"approve", "reject"}:
                if decision.get("final_action") != "REQUIRE_APPROVAL":
                    raise ApplicationError(
                        "INVALID_STATE_TRANSITION", "action is not awaiting review", 409
                    )
                if assessment_hash != decision.get("assessment_hash"):
                    raise ApplicationError(
                        "STALE_REVIEW_RESPONSE", "risk snapshot does not match", 409
                    )
                response = HumanReviewResponse(
                    approved=resolution == "approve", action_id=action_id,
                    assessment_hash=assessment_hash, reviewer=actor,
                )
                resume_response = response
            elif resolution == "provide_context":
                if decision.get("final_action") != "REQUEST_CONTEXT":
                    raise ApplicationError(
                        "INVALID_STATE_TRANSITION", "action is not awaiting context", 409
                    )
                response = ContextResponse(
                    action_id=action_id, updates=updates or {}, supplied_by=actor,
                    provenance=provenance or "operator supplied context",
                )
                resume_response = response
            else:
                raise ApplicationError("INVALID_RESOLUTION", "unsupported resolution", 422)
            resolution_event = (
                "context_supplied" if resolution == "provide_context" else "review_resolved"
            )
            await self._event(
                action_id, row["audit_id"], resolution_event,
                {"resolution": resolution, "actor": actor},
            )
            try:
                if resolution in {"approve", "reject"}:
                    result = await workflow.resume_review(action_id, resume_response)
                else:
                    result = await workflow.resume_context(action_id, resume_response)
                self.repository.save_workflow_state(action_id, result)
            except Exception as exc:
                raise ApplicationError(
                    "WORKFLOW_RESUME_ERROR", "workflow resume failed safely", 500
                ) from exc
            return self.get_action(action_id)

    def get_action(self, action_id: str) -> dict[str, Any]:
        row = self.repository.get_action(action_id)
        if row is None:
            raise ApplicationError("ACTION_NOT_FOUND", "action not found", 404)
        state = row.pop("state") or {}
        context = None
        if state.get("accounting_state"):
            safe = AccountingState.model_validate(state["accounting_state"]).inference_view()
            context = {
                "candidate_matches": safe["candidate_matches"],
                "business_context": safe["business_context"],
                "deterministic_features": safe["deterministic_features"],
                "schema_version": safe["schema_version"],
                "feature_version": safe["feature_version"],
            }
        return {
            **row,
            "context": context,
            "provider_outcome": self._public_provider_outcome(state.get("provider_outcome")),
            "policy_decision": state.get("policy_decision"),
            "human_response": state.get("human_response"),
            "execution_result": state.get("execution_result"),
            "execution_authorization": self.repository.get_execution_authorization(action_id),
            "error_state": state.get("error_state"),
            "audit_events": self.repository.events_for_action(action_id),
        }

    @staticmethod
    def _public_provider_outcome(outcome: dict[str, Any] | None) -> dict[str, Any] | None:
        if not outcome:
            return outcome
        if outcome.get("outcome") == "failure":
            return {
                key: outcome.get(key)
                for key in (
                    "provider", "code", "retryable", "latency_ms", "model_name", "outcome"
                )
            }
        return outcome

    def list_actions(self, **filters: Any) -> list[dict[str, Any]]:
        rows = self.repository.list_actions(**filters)
        return [
            {
                key: value for key, value in row.items()
                if key not in {"state"}
            }
            for row in rows
        ]

    def benchmarks(self) -> dict[str, Any]:
        if not self.benchmark_dir.is_dir():
            return {"status": "not_run", "runs": []}
        runs = []
        for path in sorted(self.benchmark_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                runs.append(
                    {
                        key: payload.get(key)
                        for key in (
                            "run_id", "created_at", "provider", "model_name",
                            "sample_size", "metrics", "measured_cost_usd",
                        )
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        return {"status": "measured" if runs else "not_run", "runs": runs}

    async def _event(
        self, action_id: str, audit_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        event = self.repository.append_event(action_id, audit_id, event_type, payload)
        await self.event_bus.publish(event)

    async def _new_workflow(
        self, provider: Any, action_id: str, audit_id: str
    ) -> LedgerGuardWorkflow:
        checkpointer = await self._get_checkpointer()

        async def event_sink(event_type: str, payload: dict[str, Any]) -> None:
            await self._event(action_id, audit_id, event_type, payload)

        return LedgerGuardWorkflow(
            self.context_builder, provider, self.policy,
            execution_tool=PersistentSimulatedExecutionTool(self.repository),
            checkpointer=checkpointer,
            event_sink=event_sink,
        )

    async def _get_checkpointer(self) -> Any | None:
        if self.checkpoint_path is None:
            return None
        if self._checkpointer is not None:
            return self._checkpointer
        async with self._checkpoint_lock:
            if self._checkpointer is None:
                self._checkpointer = await create_sqlite_checkpointer(self.checkpoint_path)
        return self._checkpointer

    async def aclose(self) -> None:
        await self.providers.aclose()
        if self._checkpointer is not None:
            await self._checkpointer.conn.close()
        self.repository.close()
