from __future__ import annotations

from backend.app.models.scenario import Scenario
from backend.app.models.state import AccountingState, BusinessContext, CandidateMatch


def build_accounting_state(
    scenario: Scenario,
) -> AccountingState:
    """
    Build the canonical provider-neutral AccountingState.

    IMPORTANT:
    The live application and evaluation pipeline must both use
    this exact function.

    No eval-only serialization or alternate state representation.
    """

    action = scenario.proposed_action

    raw_candidate_matches = scenario.original_data.get(
        "candidate_matches",
        []
    )

    candidate_matches = [
        CandidateMatch.model_validate(item)
        for item in raw_candidate_matches
    ]

    business_context_data = scenario.original_data.get(
        "business_context",
        {}
    )

    business_context = BusinessContext.model_validate(
        business_context_data
    )

    recent_ledger_history = scenario.original_data.get(
        "recent_ledger_history",
        []
    )

    deterministic_features = scenario.original_data.get(
        "deterministic_features",
        {}
    )

    return AccountingState(
        proposed_action=action,
        candidate_matches=candidate_matches,
        business_context=business_context,
        recent_ledger_history=recent_ledger_history,
        deterministic_features=deterministic_features,
        scenario_id=scenario.scenario_id,
    )
