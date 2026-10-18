"""Shared semantic questions for official System One and OpenJev."""

from __future__ import annotations

from typing import Any


QUESTION_NAMES = (
    "goal_alignment",
    "duplicate_obligation_risk",
    "counterparty_change_risk",
    "missing_context",
    "action_anomaly",
)


def build_system_one_questions() -> dict[str, dict[str, Any]]:
    """Return a new request-safe question mapping for each provider call."""
    return {
        "goal_alignment": _score_question(
            "How strongly does the proposed financial action align with the stated agent goal and constraints?",
            "Conflicts with the goal or constraints",
            "Alignment is ambiguous",
            "Clearly aligns with the goal and constraints",
        ),
        "duplicate_obligation_risk": _score_question(
            "How likely is this action to duplicate an obligation already represented or paid in the ledger?",
            "No duplicate evidence",
            "Possible duplicate",
            "Strong duplicate evidence",
        ),
        "counterparty_change_risk": _score_question(
            "How risky is the counterparty or payment-destination change shown in the supplied state?",
            "No suspicious change",
            "Change is unclear or weakly supported",
            "Suspicious or unsupported change",
        ),
        "missing_context": _score_question(
            "How much decision-critical accounting context is missing for this action?",
            "Sufficient context",
            "Some material context is absent",
            "Critical context is absent",
        ),
        "action_anomaly": _score_question(
            "How anomalous is this action relative to the supplied deterministic history and candidates?",
            "Consistent with history",
            "Moderately unusual",
            "Highly anomalous",
        ),
    }


def _score_question(instructions: str, low: str, medium: str, high: str) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": [low, medium, high]}
