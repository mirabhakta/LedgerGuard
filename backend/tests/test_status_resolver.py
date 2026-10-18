from datetime import date
from decimal import Decimal

from backend.app.models import CanonicalAccountingRecord, RecordType, SourceMetadata
from backend.app.services.status_resolver import derive_bill_status


def _record(record_type: RecordType, source_id: str, amount: str, day: int, **raw):
    return CanonicalAccountingRecord(
        record_id=f"c:{record_type.value}:{source_id}", source_id=source_id,
        company_id="c", dataset_id="w", record_type=record_type,
        timestamp=date(2025, 1, day), due_date=date(2025, 1, 5) if record_type is RecordType.BILL else None,
        amount=Decimal(amount), currency="USD", raw_metadata=raw,
        source=SourceMetadata(repository="test", relative_path="test.yaml"),
    )


def test_status_is_derived_as_of_without_future_payments() -> None:
    bill = _record(RecordType.BILL, "b1", "100", 1)
    partial = _record(
        RecordType.BILL_PAYMENT, "p1", "40", 4,
        applications=[{"document_id": "b1", "amount": "40"}],
    )
    future = _record(
        RecordType.BILL_PAYMENT, "p2", "60", 20,
        applications=[{"document_id": "b1", "amount": "60"}],
    )
    assert derive_bill_status(bill, (partial, future), as_of=date(2025, 1, 3)).status == "OPEN"
    assert derive_bill_status(bill, (partial, future), as_of=date(2025, 1, 4)).status == "PARTIALLY_PAID"
    assert derive_bill_status(bill, (partial, future), as_of=date(2025, 1, 10)).status == "PARTIALLY_PAID"
    assert derive_bill_status(bill, (partial, future), as_of=date(2025, 1, 20)).status == "PAID"


def test_unpaid_past_due_bill_is_overdue() -> None:
    bill = _record(RecordType.BILL, "b1", "100", 1)
    assert derive_bill_status(bill, (), as_of=date(2025, 1, 6)).status == "OVERDUE"
