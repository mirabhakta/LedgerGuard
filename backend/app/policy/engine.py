"""The sole deterministic authority for final financial actions."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from backend.app.models.action import ProposedAction
from backend.app.models.policy import FinalAction, PolicyDecision, PrecheckResult, TriggeredThreshold
from backend.app.models.risk import ProviderFailure, ProviderOutcome

from . import reasons
from .config import PolicyConfig


class PolicyEngine:
    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def decide(
        self,
        action: ProposedAction,
        precheck: PrecheckResult,
        outcome: ProviderOutcome | None,
        *,
        audit_id: str | None = None,
    ) -> PolicyDecision:
        evaluated: list[str] = ["hard_precheck"]
        if precheck.hard_violation:
            return self._decision(
                action, FinalAction.BLOCK, precheck.reason_codes, (), outcome,
                evaluated, audit_id,
            )
        if outcome is None:
            failure = ProviderFailure(
                provider="none", code="CONFIGURATION_ERROR",
                message="semantic provider outcome is missing", retryable=False, latency_ms=0,
            )
            return self._provider_failure(action, failure, evaluated, audit_id)
        if isinstance(outcome, ProviderFailure):
            return self._provider_failure(action, outcome, evaluated, audit_id)

        checks = (
            ("duplicate", outcome.duplicate_obligation_probability,
             outcome.duplicate_obligation_confidence,
             self.config.duplicate_block_threshold, FinalAction.BLOCK, reasons.DUPLICATE_RISK),
            ("counterparty", outcome.counterparty_change_score,
             outcome.counterparty_change_confidence,
             self.config.counterparty_review_threshold, FinalAction.REQUIRE_APPROVAL,
             reasons.COUNTERPARTY_CHANGE_RISK),
            ("missing_context", outcome.missing_context_probability,
             outcome.missing_context_confidence,
             self.config.missing_context_threshold, FinalAction.REQUEST_CONTEXT,
             reasons.MISSING_CONTEXT),
            ("anomaly", outcome.action_anomaly_score,
             outcome.action_anomaly_confidence,
             self.config.anomaly_review_threshold, FinalAction.REQUIRE_APPROVAL,
             reasons.ACTION_ANOMALY),
        )
        for name, actual, confidence, threshold, final_action, reason in checks:
            evaluated.append(name)
            if actual >= threshold:
                if confidence < self.config.minimum_confidence:
                    if name == "missing_context":
                        continue
                    return self._low_confidence_decision(
                        action, outcome, evaluated, audit_id, {name: confidence}
                    )
                hit = TriggeredThreshold(
                    name=name, comparator=">=", threshold=threshold, actual=actual
                )
                return self._decision(
                    action, final_action, (reason,), (hit,), outcome,
                    evaluated, audit_id,
                )
            if name == "duplicate":
                evaluated.append("goal_alignment")
                if outcome.goal_alignment_probability < self.config.minimum_goal_alignment:
                    if outcome.goal_alignment_confidence < self.config.minimum_confidence:
                        return self._low_confidence_decision(
                            action,
                            outcome,
                            evaluated,
                            audit_id,
                            {"goal_alignment": outcome.goal_alignment_confidence},
                        )
                    hit = TriggeredThreshold(
                        name="goal_alignment", comparator="<",
                        threshold=self.config.minimum_goal_alignment,
                        actual=outcome.goal_alignment_probability,
                    )
                    return self._decision(
                        action, FinalAction.REQUIRE_APPROVAL, (reasons.GOAL_MISMATCH,),
                        (hit,), outcome, evaluated, audit_id,
                    )
        confidences = {
            "goal_alignment": outcome.goal_alignment_confidence,
            # "duplicate": outcome.duplicate_obligation_confidence,
            # "counterparty": outcome.counterparty_change_confidence,
            # "missing_context": outcome.missing_context_confidence,
            # "anomaly": outcome.action_anomaly_confidence,
        }
        evaluated.append("minimum_confidence")
        low = {name: value for name, value in confidences.items() if value < self.config.minimum_confidence}
        if low:
            return self._low_confidence_decision(action, outcome, evaluated, audit_id, low)
        evaluated.append("allow")
        return self._decision(
            action, FinalAction.ALLOW, (reasons.POLICY_ALLOW,), (), outcome,
            evaluated, audit_id,
        )

    def _provider_failure(
        self, action: ProposedAction, failure: ProviderFailure,
        evaluated: list[str], audit_id: str | None,
    ) -> PolicyDecision:
        evaluated.append("provider_failure")
        return self._decision(
            action, self.config.provider_failure_fallback,
            (f"PROVIDER_{failure.code.value}",), (), failure, evaluated, audit_id,
        )

    def _low_confidence_decision(
        self,
        action: ProposedAction,
        outcome: ProviderOutcome,
        evaluated: list[str],
        audit_id: str | None,
        low: dict[str, float],
    ) -> PolicyDecision:
        """Low-confidence semantic evidence is reviewed, never acted on automatically."""
        hits = tuple(
            TriggeredThreshold(
                name=f"{name}_confidence", comparator="<",
                threshold=self.config.minimum_confidence,
                actual=value,
            )
            for name, value in sorted(low.items())
        )
        return self._decision(
            action,
            FinalAction.REQUIRE_APPROVAL,
            (reasons.LOW_CONFIDENCE,),
            hits,
            outcome,
            evaluated,
            audit_id,
        )

    def _decision(
        self, action: ProposedAction, final_action: FinalAction,
        reason_codes: tuple[str, ...], thresholds: tuple[TriggeredThreshold, ...],
        outcome: ProviderOutcome | None, evaluated: list[str], audit_id: str | None,
    ) -> PolicyDecision:
        assessment_hash = None
        provider = "none"
        if outcome is not None:
            provider = outcome.provider
            assessment_hash = hashlib.sha256(
                json.dumps(outcome.model_dump(mode="json"), sort_keys=True).encode()
            ).hexdigest()
        return PolicyDecision(
            final_action=final_action, reason_codes=reason_codes,
            triggered_thresholds=thresholds, provider=provider,
            audit_id=audit_id or f"audit-{uuid4().hex}", action_id=action.action_id,
            config_version=self.config.version, config_hash=self.config.stable_hash(),
            assessment_hash=assessment_hash, evaluated_rules=tuple(evaluated),
        )
