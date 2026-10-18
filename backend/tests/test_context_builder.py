from datetime import datetime, timezone
from decimal import Decimal

from backend.app.data import QuickBooksDatasetLoader, QuickBooksNormalizer
from backend.app.data.store import NormalizedAccountingStore
from backend.app.models import ActionType, ProposedAction, SyntheticDestinationMetadata
from backend.app.services.context_builder import ContextBuilder, accounting_state_hash


def _builder(dataset_root):
    loader = QuickBooksDatasetLoader(dataset_root)
    store = NormalizedAccountingStore(loader, QuickBooksNormalizer())
    return ContextBuilder(store, recent_history_limit=8, recent_history_days=14)


def _action(**changes):
    values = {
        "action_id": "action-1",
        "action_type": ActionType.PAY_VENDOR_BILL,
        "company_id": "company-001",
        "timestamp": datetime(2025, 10, 22, 12, tzinfo=timezone.utc),
        "amount": Decimal("10367.94"),
        "currency": "USD",
        "vendor_id": "vend-supplier",
        "source_document_id": "bill-00034",
        "agent_goal": "Pay the supplier bill",
    }
    values.update(changes)
    return ProposedAction(**values)


def test_real_dataset_build_is_bounded_deterministic_and_leak_free(dataset_root) -> None:
    builder = _builder(dataset_root)
    state = builder.build(_action())
    rebuilt = builder.build(_action())
    assert state.business_context.company_id == "company-001"
    assert len(state.candidate_matches) <= 5
    assert len(state.recent_ledger_history) <= 8
    assert all(record.timestamp <= _action().timestamp.date() for record in state.recent_ledger_history)
    assert accounting_state_hash(state) == accounting_state_hash(rebuilt)
    serialized = str(state.inference_view())
    assert "sim_" not in serialized
    assert "provenance_note" not in serialized
    assert "raw_metadata" not in serialized


def test_destination_is_unavailable_unless_explicitly_synthetic(dataset_root) -> None:
    builder = _builder(dataset_root)
    assert builder.build(_action()).business_context.previous_payment_destinations is None
    synthetic = SyntheticDestinationMetadata(
        previous_destination="routing-old", new_destination="routing-new",
        modification_reason="demo attack scenario", source_record_ids=("bill-00034",),
    )
    state = builder.build(_action(destination=synthetic))
    assert state.business_context.previous_payment_destinations == (
        "routing-old", "routing-new"
    )


def test_future_action_sees_more_records_but_never_changes_past_snapshot(dataset_root) -> None:
    builder = _builder(dataset_root)
    past = builder.build(_action(timestamp=datetime(2025, 10, 12, tzinfo=timezone.utc)))
    future = builder.build(_action(timestamp=datetime(2025, 11, 12, tzinfo=timezone.utc)))
    assert past.deterministic_features["visible_transaction_count"] < future.deterministic_features["visible_transaction_count"]
    assert all(record.timestamp <= datetime(2025, 10, 12).date() for record in past.recent_ledger_history)
