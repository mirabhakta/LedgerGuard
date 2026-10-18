"""Build the single provider-neutral accounting-state snapshot."""

from __future__ import annotations

import hashlib
import json
from datetime import date

from backend.app.data.store import NormalizedAccountingStore
from backend.app.models.accounting import CanonicalAccountingRecord, RecordType
from backend.app.models.action import ProposedAction
from backend.app.models.state import AccountingState, BusinessContext

from .candidate_matcher import CandidateMatcher
from .feature_calculator import calculate_amount_features, historical_amount_stats
from .status_resolver import derive_bill_status


class ContextBuilder:
    def __init__(
        self,
        store: NormalizedAccountingStore,
        *,
        candidate_limit: int = 5,
        candidate_window_days: int = 90,
        recent_history_limit: int = 20,
        recent_history_days: int = 30,
    ) -> None:
        self.store = store
        self.matcher = CandidateMatcher(top_k=candidate_limit, window_days=candidate_window_days)
        self.recent_history_limit = recent_history_limit
        self.recent_history_days = recent_history_days

    def build(self, action: ProposedAction) -> AccountingState:
        # This lookup is also the company-scope guard.
        profile = self.store.company_profile(action.company_id)
        as_of = action.timestamp.date()
        all_records = self.store.transaction_records(action.company_id)
        visible = tuple(
            record
            for record in all_records
            if record.timestamp is not None and record.timestamp <= as_of
        )
        payments = self.store.records(action.company_id, RecordType.BILL_PAYMENT)
        resolved = tuple(
            derive_bill_status(record, payments, as_of=as_of)
            if record.record_type is RecordType.BILL
            else record
            for record in visible
        )
        party_id = action.vendor_id or action.counterparty_id
        vendor_history = [
            record
            for record in resolved
            if party_id
            and party_id in {record.vendor_id, record.counterparty_id}
            and record.amount is not None
            and record.record_type in {RecordType.BILL, RecordType.BILL_PAYMENT}
        ]
        amounts = [record.amount for record in vendor_history if record.amount is not None]
        stats = historical_amount_stats(amounts)
        category_history = tuple(
            dict.fromkeys(record.category for record in vendor_history if record.category)
        )
        account_history = tuple(
            dict.fromkeys(
                reference.account_id
                for record in vendor_history
                for reference in record.account_references
            )
        )
        cutoff_ordinal = as_of.toordinal() - self.recent_history_days
        recent = tuple(
            sorted(
                (
                    record
                    for record in resolved
                    if record.timestamp is not None
                    and record.timestamp.toordinal() >= cutoff_ordinal
                ),
                key=lambda record: (record.timestamp or date.min, record.record_id),
                reverse=True,
            )[: self.recent_history_limit]
        )
        destination_history = None
        if action.destination is not None:
            destination_history = tuple(
                value
                for value in (
                    action.destination.previous_destination,
                    action.destination.new_destination,
                )
                if value
            )
        features = calculate_amount_features(action.amount, stats, amounts)
        features.update(
            {
                "as_of_date": as_of.isoformat(),
                "visible_transaction_count": len(visible),
                "candidate_window_days": self.matcher.window_days,
                "recent_history_days": self.recent_history_days,
            }
        )
        return AccountingState(
            proposed_action=action,
            candidate_matches=self.matcher.match(action, resolved),
            business_context=BusinessContext(
                company_id=action.company_id,
                business_type=str(profile.get("profile")) if profile.get("profile") else None,
                industry_naics=(
                    str(profile.get("industry_naics")) if profile.get("industry_naics") else None
                ),
                current_account_id=action.account_id,
                vendor_transaction_count=len(vendor_history),
                historical_amount_stats=stats,
                category_history=category_history,
                account_history=account_history,
                previous_payment_destinations=destination_history,
                user_constraints=action.user_constraints,
            ),
            recent_ledger_history=recent,
            deterministic_features=features,
            schema_version="1",
            feature_version="1",
        )


def accounting_state_hash(state: AccountingState) -> str:
    payload = json.dumps(
        state.inference_view(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
