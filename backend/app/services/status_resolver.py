"""As-of status derivation from payment applications."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.models.accounting import CanonicalAccountingRecord, RecordType, StatusSource


def derive_bill_status(
    bill: CanonicalAccountingRecord,
    payments: tuple[CanonicalAccountingRecord, ...],
    *,
    as_of: date,
) -> CanonicalAccountingRecord:
    if bill.record_type is not RecordType.BILL or bill.amount is None:
        return bill
    paid = Decimal("0")
    for payment in payments:
        if payment.company_id != bill.company_id or payment.timestamp is None:
            continue
        if payment.timestamp > as_of:
            continue
        for application in payment.raw_metadata.get("applications", []):
            if isinstance(application, dict) and application.get("document_id") == bill.source_id:
                value = application.get("amount")
                if value is not None:
                    paid += Decimal(str(value))
    if paid >= bill.amount:
        status = "PAID"
    elif paid > 0:
        status = "PARTIALLY_PAID"
    elif bill.due_date is not None and bill.due_date < as_of:
        status = "OVERDUE"
    else:
        status = "OPEN"
    return bill.model_copy(
        update={
            "status": status,
            "status_source": StatusSource.DERIVED_AS_OF,
            "raw_metadata": {
                **bill.raw_metadata,
                "derived_as_of": as_of.isoformat(),
                "derived_paid_amount": str(paid),
                "derived_open_balance": str(max(bill.amount - paid, Decimal("0"))),
            },
        }
    )
