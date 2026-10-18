"""Deterministic facts evaluated before semantic authorization."""

from backend.app.models.action import ActionType, ProposedAction
from backend.app.models.policy import PrecheckFact, PrecheckResult
from backend.app.models.state import AccountingState

from . import reasons
from .config import PolicyConfig


def run_prechecks(
    action: ProposedAction,
    state: AccountingState,
    config: PolicyConfig,
    *,
    known_account_ids: frozenset[str] | None = None,
) -> PrecheckResult:
    facts: list[PrecheckFact] = []
    violations: list[str] = []

    def check(code: str, passed: bool, detail: str) -> None:
        facts.append(PrecheckFact(code=code, passed=passed, detail=detail))
        if not passed:
            violations.append(code)

    check(
        reasons.UNSUPPORTED_ACTION_TYPE,
        action.action_type in config.supported_action_types,
        f"action_type={action.action_type.value}",
    )
    check(
        reasons.UNSUPPORTED_CURRENCY,
        action.currency.upper() in config.supported_currencies,
        f"currency={action.currency.upper()}",
    )
    check(
        reasons.HARD_LIMIT_EXCEEDED,
        action.amount <= config.absolute_amount_hard_limit,
        f"amount={action.amount}; limit={config.absolute_amount_hard_limit}",
    )
    candidate_scope_valid = all(
        candidate.ledger_id.startswith(f"{action.company_id}:")
        for candidate in state.candidate_matches
    )
    check(
        reasons.CROSS_COMPANY_CONTEXT,
        action.company_id == state.business_context.company_id
        and action.company_id == state.proposed_action.company_id
        and candidate_scope_valid,
        "action and accounting state must share company scope",
    )
    required_reference_present = (
        action.action_type is not ActionType.PAY_VENDOR_BILL
        or bool(action.source_document_id and (action.vendor_id or action.counterparty_id))
    )
    check(
        reasons.MISSING_REQUIRED_REFERENCE,
        required_reference_present,
        "vendor bill payments require a vendor/counterparty and source document",
    )
    account_valid = (
        action.account_id is None
        or known_account_ids is None
        or action.account_id in known_account_ids
    )
    check(reasons.UNKNOWN_ACCOUNT, account_valid, f"account_id={action.account_id}")
    exact_paid = any(
        action.source_document_id
        and candidate.source_id == action.source_document_id
        and candidate.status == "PAID"
        for candidate in state.candidate_matches
    )
    check(
        reasons.EXACT_PAID_DOCUMENT_DUPLICATE,
        not exact_paid,
        f"source_document_id={action.source_document_id}",
    )
    return PrecheckResult(
        hard_violation=bool(violations),
        reason_codes=tuple(violations),
        facts=tuple(facts),
    )
