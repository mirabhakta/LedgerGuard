from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.models import (
    AccountingState, ActionType, BusinessContext, CandidateMatch, HistoricalAmountStats,
    ProposedAction,
)
from backend.app.policy import PolicyConfig, run_prechecks


def _action(**changes):
    values = {
        "action_id": "a1", "action_type": ActionType.PAY_VENDOR_BILL,
        "company_id": "company-001", "timestamp": datetime(2025, 1, 2, tzinfo=timezone.utc),
        "amount": Decimal("100"), "currency": "USD", "vendor_id": "v1",
        "source_document_id": "b1", "account_id": "acct-1", "agent_goal": "pay",
    }
    values.update(changes)
    return ProposedAction(**values)


def _state(action, candidates=()):
    return AccountingState(
        proposed_action=action, candidate_matches=candidates,
        business_context=BusinessContext(
            company_id=action.company_id, vendor_transaction_count=0,
            historical_amount_stats=HistoricalAmountStats(observation_count=0),
        ), recent_ledger_history=(), deterministic_features={},
    )


def test_clean_action_preserves_all_passing_facts() -> None:
    action = _action()
    result = run_prechecks(action, _state(action), PolicyConfig(), known_account_ids=frozenset({"acct-1"}))
    assert not result.hard_violation
    assert result.reason_codes == ()
    assert all(fact.passed for fact in result.facts)


def test_currency_limit_account_and_required_reference_are_hard_failures() -> None:
    action = _action(currency="EUR", amount=Decimal("100001"), account_id="unknown", vendor_id=None)
    result = run_prechecks(action, _state(action), PolicyConfig(), known_account_ids=frozenset({"acct-1"}))
    assert result.hard_violation
    assert {"UNSUPPORTED_CURRENCY", "HARD_LIMIT_EXCEEDED", "UNKNOWN_ACCOUNT", "MISSING_REQUIRED_REFERENCE"} <= set(result.reason_codes)


def test_exact_paid_document_and_cross_company_candidate_block() -> None:
    action = _action()
    candidate = CandidateMatch(
        ledger_id="company-002:bill:b1", source_id="b1", record_type="bill",
        date=date(2025, 1, 1), amount=Decimal("100"), status="PAID",
        match_score=1, match_reasons=("EXACT_DOCUMENT_LINK",),
    )
    result = run_prechecks(action, _state(action, (candidate,)), PolicyConfig())
    assert "CROSS_COMPANY_CONTEXT" in result.reason_codes
    assert "EXACT_PAID_DOCUMENT_DUPLICATE" in result.reason_codes
