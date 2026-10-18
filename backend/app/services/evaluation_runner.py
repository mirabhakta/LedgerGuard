"""Fair provider evaluation over immutable shared cases."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from backend.app.models.policy import FinalAction, PolicyDecision, PrecheckResult
from backend.app.models.risk import ProviderFailure
from backend.app.models.scenario import Scenario
from backend.app.models.state import AccountingState
from backend.app.policy.engine import PolicyEngine
from backend.app.providers.base import DecisionProvider
from backend.app.services.context_builder import accounting_state_hash

from .metrics import EvaluationMetrics, MetricInput, calculate_metrics


class EvaluationCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str
    scenario_version: str
    source_record_ids: tuple[str, ...]
    expected_action: FinalAction
    expected_risk_flags: tuple[str, ...]
    state: AccountingState
    state_hash: str
    precheck: PrecheckResult

    @classmethod
    def from_scenario(
        cls, scenario: Scenario, state: AccountingState, precheck: PrecheckResult
    ) -> "EvaluationCase":
        return cls(
            scenario_id=scenario.scenario_id, scenario_version=scenario.schema_version,
            source_record_ids=scenario.source_record_ids,
            expected_action=scenario.expected_action,
            expected_risk_flags=scenario.expected_risk_flags,
            state=state, state_hash=accounting_state_hash(state), precheck=precheck,
        )


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    scenario_id: str
    scenario_version: str
    state_hash: str
    expected_action: FinalAction
    provider: str
    model_name: str | None
    provider_failed: bool
    provider_latency_ms: float
    end_to_end_latency_ms: float
    policy_config_hash: str
    decision: PolicyDecision


class EvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    created_at: datetime
    provider: str
    model_name: str | None
    sample_size: int
    case_set_hash: str
    policy_config_hash: str
    metrics: EvaluationMetrics
    results: tuple[EvaluationResult, ...]
    measured_cost_usd: float | None = None


class EvaluationRunner:
    def __init__(self, policy: PolicyEngine) -> None:
        self.policy = policy

    async def run(
        self,
        cases: tuple[EvaluationCase, ...],
        provider: DecisionProvider,
        *,
        output_dir: Path | None = None,
    ) -> EvaluationRun:
        _validate_cases(cases)
        run_id = f"eval-{uuid4().hex}"
        results: list[EvaluationResult] = []
        for case in cases:
            started = time.monotonic()
            outcome = await provider.evaluate(case.state)
            decision = self.policy.decide(
                case.state.proposed_action, case.precheck, outcome,
                audit_id=f"{run_id}:{case.scenario_id}",
            )
            elapsed = (time.monotonic() - started) * 1000
            results.append(
                EvaluationResult(
                    run_id=run_id, scenario_id=case.scenario_id,
                    scenario_version=case.scenario_version, state_hash=case.state_hash,
                    expected_action=case.expected_action, provider=outcome.provider,
                    model_name=getattr(outcome, "model_name", None),
                    provider_failed=isinstance(outcome, ProviderFailure),
                    provider_latency_ms=outcome.latency_ms,
                    end_to_end_latency_ms=elapsed,
                    policy_config_hash=self.policy.config.stable_hash(), decision=decision,
                )
            )
        metrics = calculate_metrics(
            [
                MetricInput(
                    expected_action=item.expected_action,
                    predicted_action=item.decision.final_action,
                    latency_ms=item.provider_latency_ms,
                    provider_failed=item.provider_failed,
                )
                for item in results
            ]
        )
        model_names = {item.model_name for item in results}
        run = EvaluationRun(
            run_id=run_id, created_at=datetime.now(timezone.utc),
            provider=results[0].provider if results else "unknown",
            model_name=next(iter(model_names)) if len(model_names) == 1 else None,
            sample_size=len(results), case_set_hash=_case_set_hash(cases),
            policy_config_hash=self.policy.config.stable_hash(), metrics=metrics,
            results=tuple(results), measured_cost_usd=None,
        )
        if output_dir is not None:
            write_run_artifacts(run, output_dir)
        return run


def assert_fair_comparison(runs: tuple[EvaluationRun, ...]) -> None:
    if not runs:
        raise ValueError("at least one run is required")
    baseline = runs[0]
    baseline_cases = [
        (item.scenario_id, item.scenario_version, item.state_hash, item.expected_action)
        for item in baseline.results
    ]
    for run in runs[1:]:
        cases = [
            (item.scenario_id, item.scenario_version, item.state_hash, item.expected_action)
            for item in run.results
        ]
        if cases != baseline_cases:
            raise ValueError("evaluation case IDs, labels, versions, or state hashes differ")
        if run.policy_config_hash != baseline.policy_config_hash:
            raise ValueError("policy config hashes differ")


def write_run_artifacts(run: EvaluationRun, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{run.created_at.date().isoformat()}-{run.provider}-{run.run_id}"
    (output_dir / f"{stem}.json").write_text(
        json.dumps(run.model_dump(mode="json"), sort_keys=True, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    with (output_dir / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "run_id", "scenario_id", "state_hash", "expected_action",
                "predicted_action", "provider", "model_name", "provider_failed",
                "provider_latency_ms", "end_to_end_latency_ms",                 "policy_config_hash",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for result in run.results:
            writer.writerow(
                {
                    "run_id": result.run_id, "scenario_id": result.scenario_id,
                    "state_hash": result.state_hash, "expected_action": result.expected_action.value,
                    "predicted_action": result.decision.final_action.value,
                    "provider": result.provider, "model_name": result.model_name,
                    "provider_failed": result.provider_failed,
                    "provider_latency_ms": result.provider_latency_ms,
                    "end_to_end_latency_ms": result.end_to_end_latency_ms,
                    "policy_config_hash": result.policy_config_hash,
                }
            )


def _validate_cases(cases: tuple[EvaluationCase, ...]) -> None:
    ids = [case.scenario_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("evaluation scenario IDs must be unique")
    for case in cases:
        if accounting_state_hash(case.state) != case.state_hash:
            raise ValueError(f"state hash mismatch for {case.scenario_id}")


def _case_set_hash(cases: tuple[EvaluationCase, ...]) -> str:
    payload = [
        (case.scenario_id, case.scenario_version, case.state_hash, case.expected_action.value)
        for case in cases
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
