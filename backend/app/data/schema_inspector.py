"""Deterministic source-schema checks for RWM v4."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.accounting import RecordType
from backend.app.models.errors import SchemaDriftError

from .loader import QuickBooksDatasetLoader


@dataclass(frozen=True, slots=True)
class CompanyInspection:
    company_id: str
    schema_version: str
    realize_version: str
    currency: str
    actual_counts: dict[str, int]


class DatasetSchemaInspector:
    def __init__(
        self,
        loader: QuickBooksDatasetLoader,
        *,
        supported_schema_versions: frozenset[str] = frozenset({"4"}),
    ) -> None:
        self.loader = loader
        self.supported_schema_versions = supported_schema_versions

    def inspect_company(self, company_id: str) -> CompanyInspection:
        manifest = self.loader.manifest(company_id)
        schema_version = str(manifest.get("schema_version", ""))
        if schema_version not in self.supported_schema_versions:
            raise SchemaDriftError(
                f"unsupported schema version for {company_id}: {schema_version!r}"
            )
        currency = manifest.get("currency")
        if not isinstance(currency, str) or len(currency) != 3:
            raise SchemaDriftError(f"invalid manifest currency for {company_id}")

        actual_counts: dict[str, int] = {}
        for record_type in RecordType:
            actual_counts[record_type.value] = len(
                self.loader.load_entity(company_id, record_type)
            )

        expected = self.loader.index_row(company_id).get("entity_counts", {})
        for record_type in RecordType:
            expected_key = _index_count_key(record_type)
            if expected_key in expected and expected[expected_key] != actual_counts[record_type.value]:
                raise SchemaDriftError(
                    f"count mismatch for {company_id}/{expected_key}: "
                    f"index={expected[expected_key]} actual={actual_counts[record_type.value]}"
                )

        return CompanyInspection(
            company_id=company_id,
            schema_version=schema_version,
            realize_version=str(manifest.get("realize_version", "")),
            currency=currency,
            actual_counts=actual_counts,
        )


def _index_count_key(record_type: RecordType) -> str:
    return {
        RecordType.COMPANY: "company",
        RecordType.ACCOUNT: "accounts",
        RecordType.CUSTOMER: "customers",
        RecordType.VENDOR: "vendors",
        RecordType.EMPLOYEE: "employees",
        RecordType.ITEM: "items",
        RecordType.INVOICE: "invoices",
        RecordType.SALES_RECEIPT: "sales_receipts",
        RecordType.CUSTOMER_PAYMENT: "customer_payments",
        RecordType.BILL: "bills",
        RecordType.BILL_PAYMENT: "bill_payments",
        RecordType.JOURNAL_ENTRY: "journal_entries",
        RecordType.PROJECT: "projects",
        RecordType.BANK_TRANSACTION: "bank_transactions",
        RecordType.ESTIMATE: "estimates",
        RecordType.TERMS: "terms",
        RecordType.PAYROLL_RUN: "payroll_runs",
    }[record_type]

