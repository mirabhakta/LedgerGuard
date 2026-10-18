"""Label-leakage audit: what a provider sees must not reveal the label, the recipe, or the future."""

from __future__ import annotations

import re
from datetime import date

from backend.app.models.scenario import Scenario
from backend.app.models.state import AccountingState

CATEGORY_KEYS = (
    "safe_control",
    "duplicate_deposit",
    "payroll_double_count",
    "internal_transfer_as_expense",
    "ambiguous_vendor_missing_context",
    "large_but_legitimate",
    "personal_looking_expense",
    "destination_change",
    "duplicate_similar_invoice",
    "constraint_violation",
)
FORBIDDEN_TOKENS = (
    "provenance_note",
    "sim_event",
    "sim_actor",
    "sim_obligation",
    "sim_payment",
    "sim_order",
    "expected_action",
    "acceptable_actions",
    "is_unsafe",
    "expected_risk_flags",
    "disclosure_id",
    "hero_case",
)
_PATTERNS = [re.compile(rf"\b{re.escape(t)}\b") for t in CATEGORY_KEYS + FORBIDDEN_TOKENS] + [re.compile(r"\bMOD-[A-Z]?\d+")]


def find_leaks(scenario: Scenario, state: AccountingState) -> list[str]:
    payload = state.model_dump_json(exclude={"scenario_id"})
    leaks = [f"token:{p.pattern}" for p in _PATTERNS if p.search(payload)]

    rationale = scenario.metadata.get("rationale")
    if rationale and rationale in payload:
        leaks.append("label rationale text present")

    as_of = scenario.metadata.get("as_of_date")
    if as_of:
        cutoff = date.fromisoformat(as_of)
        for c in state.candidate_matches:
            if c.date and c.date >= cutoff:
                leaks.append(f"future candidate {c.record_id} dated {c.date}")
        for row in state.recent_ledger_history:
            if "date" in row and date.fromisoformat(row["date"]) >= cutoff:
                leaks.append(f"future history row {row.get('record_id')} dated {row['date']}")
    return leaks
