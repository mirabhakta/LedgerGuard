"""Raw and canonical accounting records."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecordType(StrEnum):
    COMPANY = "company"
    ACCOUNT = "account"
    CUSTOMER = "customer"
    VENDOR = "vendor"
    EMPLOYEE = "employee"
    ITEM = "item"
    INVOICE = "invoice"
    SALES_RECEIPT = "sales_receipt"
    CUSTOMER_PAYMENT = "customer_payment"
    BILL = "bill"
    BILL_PAYMENT = "bill_payment"
    JOURNAL_ENTRY = "journal_entry"
    PROJECT = "project"
    BANK_TRANSACTION = "bank_transaction"
    ESTIMATE = "estimate"
    TERMS = "terms"
    PAYROLL_RUN = "payroll_run"


class StatusSource(StrEnum):
    DIRECT = "direct"
    DERIVED_AS_OF = "derived_as_of"


class SourceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    repository: str
    archive_sha256: str | None = None
    relative_path: str
    schema_version: str | None = None


class AccountReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    role: str
    debit_amount: Decimal | None = None
    credit_amount: Decimal | None = None


class RawQuickBooksRecord(BaseModel):
    """A source row plus the scope that the YAML row does not carry."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    dataset_id: str
    record_type: RecordType
    relative_path: str
    payload: dict[str, Any]


class CanonicalAccountingRecord(BaseModel):
    """A lossless-enough canonical view used by deterministic services."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    source_id: str
    company_id: str
    dataset_id: str
    record_type: RecordType
    timestamp: date | None = None
    due_date: date | None = None
    vendor_id: str | None = None
    vendor_name: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    description: str | None = None
    memo: str | None = None
    amount: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)
    category: str | None = None
    category_source: str | None = None
    account_references: tuple[AccountReference, ...] = ()
    source_document_ids: tuple[str, ...] = ()
    invoice_id: str | None = None
    bill_id: str | None = None
    payment_id: str | None = None
    status: str | None = None
    status_source: StatusSource | None = None
    source: SourceMetadata
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    def inference_view(self) -> dict[str, Any]:
        """Return the provider-safe view, excluding generator ground truth."""

        view = self.model_dump(mode="json", exclude={"raw_metadata"})
        return _strip_generator_fields(view)


def _strip_generator_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_generator_fields(item)
            for key, item in value.items()
            if not key.startswith("sim_") and key != "provenance_note"
        }
    if isinstance(value, list):
        return [_strip_generator_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_generator_fields(item) for item in value)
    return value

