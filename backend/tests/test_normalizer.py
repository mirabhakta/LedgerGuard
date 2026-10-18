from __future__ import annotations

from decimal import Decimal

from backend.app.data.loader import QuickBooksDatasetLoader
from backend.app.data.normalizer import QuickBooksNormalizer
from backend.app.models.accounting import RecordType

ARCHIVE_SHA = "6090485212458315c6d58c2793221b79de54fa89191edccaeba2c5c1c5cb1f38"


def _normalize_first(loader: QuickBooksDatasetLoader, company: str, kind: RecordType):
    raw = loader.load_entity(company, kind)[0]
    manifest = loader.manifest(company)
    return QuickBooksNormalizer(archive_sha256=ARCHIVE_SHA).normalize(
        raw, currency=manifest["currency"], schema_version=manifest["schema_version"]
    )


def test_canonical_identity_is_company_scoped(loader: QuickBooksDatasetLoader) -> None:
    first = _normalize_first(loader, "company-001", RecordType.ACCOUNT)
    second = _normalize_first(loader, "company-002", RecordType.ACCOUNT)
    assert first.source_id == second.source_id == "acct-checking"
    assert first.record_id != second.record_id


def test_money_uses_decimal_and_preserves_bank_sign(loader: QuickBooksDatasetLoader) -> None:
    bill = _normalize_first(loader, "company-001", RecordType.BILL)
    bank_records = loader.load_entity("company-001", RecordType.BANK_TRANSACTION)
    raw_negative = next(record for record in bank_records if record.payload["amount"].startswith("-"))
    bank = QuickBooksNormalizer().normalize(raw_negative, currency="USD")
    assert bill.amount == Decimal("4098.00")
    assert isinstance(bill.amount, Decimal)
    assert bank.amount == Decimal("-750.00")


def test_bill_reference_and_currency_are_mapped_without_doc_number_identity(
    loader: QuickBooksDatasetLoader,
) -> None:
    bill = _normalize_first(loader, "company-001", RecordType.BILL)
    assert bill.bill_id == "bill-00005"
    assert bill.currency == "USD"
    assert "BILL-5001" not in bill.record_id


def test_journal_does_not_invent_a_net_amount(loader: QuickBooksDatasetLoader) -> None:
    journal = _normalize_first(loader, "company-001", RecordType.JOURNAL_ENTRY)
    assert journal.amount is None
    assert len(journal.account_references) >= 2


def test_inference_view_excludes_generator_ground_truth(loader: QuickBooksDatasetLoader) -> None:
    bill = _normalize_first(loader, "company-001", RecordType.BILL)
    serialized = str(bill.inference_view())
    assert "sim_obligation_id" not in serialized
    assert "provenance_note" not in serialized
    assert "raw_metadata" not in serialized

