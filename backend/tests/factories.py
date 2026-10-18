from __future__ import annotations

from typing import Any

from backend.app.models.action import ProposedAction
from backend.app.models.risk import RiskAssessment, RiskSignal
from backend.app.models.state import AccountingState, BusinessContext


def make_state(
    *,
    features: dict[str, Any] | None = None,
    constraints: list[str] | None = None,
    **action_fields: Any,
) -> AccountingState:
    action = {
        "action_id": "act-test",
        "action_type": "PAY_VENDOR_BILL",
        "amount": 500.0,
        "currency": "USD",
        "vendor": "Granite Bay Commercial Properties",
        "counterparty": "Granite Bay Commercial Properties",
        "destination_account": "ACH ****1234",
        "source_document_id": "bill-00042",
        "proposed_category": "Operating Expense",
        "agent_goal": "Pay all outstanding vendor bills due today.",
        "metadata": {"memo": "Monthly rent for the warehouse unit as agreed."},
        **action_fields,
    }
    base_features = {
        "action_type": action["action_type"],
        "amount": action["amount"],
        "has_source_document": bool(action["source_document_id"]),
        "vendor_known": True,
        "vendor_supply_role": "premises",
        "amount_ratio_to_vendor_median": 1.0,
        "amount_robust_z": 0.0,
        "payment_destination_known": True,
        "payment_destination_changed": False,
        "candidate_count": 0,
    }
    return AccountingState(
        proposed_action=ProposedAction(**action),
        business_context=BusinessContext(
            company_id="company-001",
            user_constraints={"rules": constraints} if constraints else {},
        ),
        deterministic_features={**base_features, **(features or {})},
    )


def make_assessment(confidence: float = 0.9, model_name: str = "test-model", **values: float) -> RiskAssessment:
    names = (
        "goal_misalignment_risk",
        "duplicate_obligation_risk",
        "counterparty_change_risk",
        "missing_context_risk",
        "action_anomaly_risk",
    )
    return RiskAssessment(
        **{n: RiskSignal(value=values.get(n, 0.0), confidence=confidence) for n in names},
        model_name=model_name,
        latency_ms=1.0,
    )
