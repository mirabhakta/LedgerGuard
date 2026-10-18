"""Transparent heuristic baseline over the shared AccountingState."""

from __future__ import annotations

import time

from backend.app.models.risk import RiskAssessment
from backend.app.models.state import AccountingState


class RulesProvider:
    name = "rules"
    model_name = "rules-v1"

    async def evaluate(self, state: AccountingState) -> RiskAssessment:
        started = time.monotonic()
        action = state.proposed_action
        goal = action.agent_goal.casefold()
        goal_alignment = 0.9
        if action.action_type.value == "PAY_VENDOR_BILL" and any(
            phrase in goal for phrase in ("do not pay", "don't pay", "stop payment")
        ):
            goal_alignment = 0.05

        duplicate = 0.05
        for candidate in state.candidate_matches:
            reasons = set(candidate.match_reasons)
            if "EXACT_DOCUMENT_LINK" in reasons and candidate.status == "PAID":
                duplicate = max(duplicate, 0.99)
            elif "EXACT_DOCUMENT_LINK" in reasons:
                duplicate = max(duplicate, 0.45)
            elif {"SAME_COUNTERPARTY", "EXACT_AMOUNT"} <= reasons:
                duplicate = max(duplicate, 0.65)

        destination = action.destination
        counterparty_change = (
            0.95
            if destination is not None
            and destination.previous_destination is not None
            and destination.previous_destination != destination.new_destination
            else 0.05
        )
        missing_context = 0.05
        if action.action_type.value == "PAY_VENDOR_BILL" and not (
            action.source_document_id and (action.vendor_id or action.counterparty_id)
        ):
            missing_context = 0.95
        elif action.action_type.value == "ADD_TRANSACTION" and not (
            action.vendor_id or action.counterparty_id or action.source_document_id
        ):
            missing_context = 0.85

        anomaly = 0.05
        raw_z = state.deterministic_features.get("z_score")
        raw_ratio = state.deterministic_features.get("ratio_to_median")
        try:
            if raw_z is not None:
                anomaly = max(anomaly, min(1.0, abs(float(raw_z)) / 4))
            if raw_ratio is not None and float(raw_ratio) >= 3:
                anomaly = max(anomaly, 0.9)
        except (TypeError, ValueError):
            anomaly = max(anomaly, 0.5)

        return RiskAssessment(
            goal_alignment_probability=goal_alignment,
            goal_alignment_confidence=0.85,
            duplicate_obligation_probability=duplicate,
            duplicate_obligation_confidence=0.90,
            counterparty_change_score=counterparty_change,
            counterparty_change_confidence=0.95 if destination is not None else 0.75,
            missing_context_probability=missing_context,
            missing_context_confidence=0.85,
            action_anomaly_score=anomaly,
            action_anomaly_confidence=0.75,
            provider=self.name,
            model_name=self.model_name,
            latency_ms=max(0.0, (time.monotonic() - started) * 1000),
        )
