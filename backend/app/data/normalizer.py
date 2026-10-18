"""Explicit RWM v4 to canonical-record normalization."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.app.models.accounting import (
    AccountReference,
    CanonicalAccountingRecord,
    RawQuickBooksRecord,
    RecordType,
    SourceMetadata,
    StatusSource,
)
from backend.app.models.errors import NormalizationError


class QuickBooksNormalizer:
    def __init__(self, *, archive_sha256: str | None = None) -> None:
        self.archive_sha256 = archive_sha256

    def normalize(
        self, raw: RawQuickBooksRecord, *, currency: str, schema_version: str = "4"
    ) -> CanonicalAccountingRecord:
        payload = raw.payload
        source_id = str(payload["id"])
        timestamp = _date(payload.get("txn_date") or payload.get("date"))
        due_date = _date(payload.get("due_date"))
        amount = _money(payload.get("total_amount", payload.get("amount")))
        vendor_id = _string(payload.get("vendor_id"))
        vendor_name = _string(payload.get("vendor_name"))
        customer_id = _string(payload.get("customer_id"))
        customer_name = _string(payload.get("customer_name"))
        counterparty_id = vendor_id or customer_id
        counterparty_name = vendor_name or customer_name
        category, category_source = _category(payload, raw.record_type)
        account_references = tuple(_account_references(payload, raw.record_type))
        source_document_ids = tuple(_source_document_ids(payload, raw.record_type))
        status = _string(payload.get("status"))

        return CanonicalAccountingRecord(
            record_id=f"{raw.company_id}:{raw.record_type.value}:{source_id}",
            source_id=source_id,
            company_id=raw.company_id,
            dataset_id=raw.dataset_id,
            record_type=raw.record_type,
            timestamp=timestamp,
            due_date=due_date,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            customer_id=customer_id,
            customer_name=customer_name,
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            description=_description(payload),
            memo=_string(payload.get("memo")),
            amount=amount,
            currency=currency.upper(),
            category=category,
            category_source=category_source,
            account_references=account_references,
            source_document_ids=source_document_ids,
            invoice_id=source_id if raw.record_type is RecordType.INVOICE else None,
            bill_id=source_id if raw.record_type is RecordType.BILL else None,
            payment_id=(
                source_id
                if raw.record_type in {RecordType.BILL_PAYMENT, RecordType.CUSTOMER_PAYMENT}
                else None
            ),
            status=status,
            status_source=StatusSource.DIRECT if status is not None else None,
            source=SourceMetadata(
                repository="CL251215/QuickBooks-Hackathon-2026",
                archive_sha256=self.archive_sha256,
                relative_path=raw.relative_path,
                schema_version=schema_version,
            ),
            raw_metadata=dict(payload),
        )


def _money(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise NormalizationError("boolean is not a valid amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise NormalizationError(f"invalid amount: {value!r}") from exc
    if not result.is_finite():
        raise NormalizationError(f"non-finite amount: {value!r}")
    if result.as_tuple().exponent < -2:
        raise NormalizationError(f"amount has more than two decimal places: {value!r}")
    return result


def _date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise NormalizationError(f"invalid ISO date: {value!r}") from exc


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _category(payload: dict[str, Any], record_type: RecordType) -> tuple[str | None, str | None]:
    fields = {
        RecordType.BILL: "cost_category",
        RecordType.JOURNAL_ENTRY: "purpose",
        RecordType.BANK_TRANSACTION: "kind",
        RecordType.PROJECT: "project_kind",
        RecordType.ESTIMATE: "project_kind",
    }
    field = fields.get(record_type)
    return (_string(payload.get(field)), field) if field else (None, None)


def _description(payload: dict[str, Any]) -> str | None:
    direct = _string(payload.get("description"))
    if direct:
        return direct
    descriptions: list[str] = []
    for field in ("lines", "item_lines", "account_lines"):
        for line in payload.get(field, []):
            if isinstance(line, dict) and isinstance(line.get("description"), str):
                descriptions.append(line["description"])
    return " | ".join(dict.fromkeys(descriptions)) or None


def _account_references(
    payload: dict[str, Any], record_type: RecordType
) -> list[AccountReference]:
    references: list[AccountReference] = []
    direct_fields = {
        "payment_account_id": "payment_source",
        "source_account_id": "collection_source",
        "deposit_account_id": "deposit",
        "income_account_id": "income",
        "retainage_account_id": "retainage",
    }
    for field, role in direct_fields.items():
        value = payload.get(field)
        if isinstance(value, str):
            references.append(AccountReference(account_id=value, role=role))

    if record_type is RecordType.JOURNAL_ENTRY:
        for line in payload.get("lines", []):
            if not isinstance(line, dict) or not isinstance(line.get("account_id"), str):
                continue
            references.append(
                AccountReference(
                    account_id=line["account_id"],
                    role="journal_line",
                    debit_amount=_money(line.get("debit_amount")),
                    credit_amount=_money(line.get("credit_amount")),
                )
            )
    if record_type is RecordType.BILL:
        for line in payload.get("account_lines", []):
            if isinstance(line, dict) and isinstance(line.get("account_id"), str):
                references.append(AccountReference(account_id=line["account_id"], role="expense"))
    return references


def _source_document_ids(payload: dict[str, Any], record_type: RecordType) -> list[str]:
    references: list[str] = []
    source_document_id = payload.get("source_document_id")
    if isinstance(source_document_id, str):
        references.append(source_document_id)
    if record_type in {RecordType.BILL_PAYMENT, RecordType.CUSTOMER_PAYMENT}:
        for application in payload.get("applications", []):
            if isinstance(application, dict) and isinstance(application.get("document_id"), str):
                references.append(application["document_id"])
    return list(dict.fromkeys(references))

