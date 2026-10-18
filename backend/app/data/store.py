"""Company-scoped access to normalized RWM v4 records."""

from __future__ import annotations

from functools import lru_cache

from backend.app.models.accounting import CanonicalAccountingRecord, RecordType

from .loader import QuickBooksDatasetLoader
from .normalizer import QuickBooksNormalizer


class NormalizedAccountingStore:
    """Normalize once per company/entity and never perform cross-company scans."""

    def __init__(self, loader: QuickBooksDatasetLoader, normalizer: QuickBooksNormalizer) -> None:
        self.loader = loader
        self.normalizer = normalizer

    @lru_cache(maxsize=512)
    def records(
        self, company_id: str, record_type: RecordType
    ) -> tuple[CanonicalAccountingRecord, ...]:
        manifest = self.loader.manifest(company_id)
        currency = str(manifest.get("currency", "USD"))
        schema_version = str(manifest.get("schema_version", "4"))
        return tuple(
            self.normalizer.normalize(
                raw, currency=currency, schema_version=schema_version
            )
            for raw in self.loader.load_entity(company_id, record_type)
        )

    def company_profile(self, company_id: str) -> dict[str, object]:
        return self.loader.index_row(company_id)

    def transaction_records(self, company_id: str) -> tuple[CanonicalAccountingRecord, ...]:
        non_transactions = {
            RecordType.COMPANY,
            RecordType.ACCOUNT,
            RecordType.CUSTOMER,
            RecordType.VENDOR,
            RecordType.EMPLOYEE,
            RecordType.ITEM,
            RecordType.PROJECT,
            RecordType.TERMS,
        }
        records: list[CanonicalAccountingRecord] = []
        for record_type in RecordType:
            if record_type not in non_transactions:
                records.extend(self.records(company_id, record_type))
        return tuple(records)
