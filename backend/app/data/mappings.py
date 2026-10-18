"""Explicit mappings from RWM v4 YAML files to canonical record types."""

from backend.app.models.accounting import RecordType

ENTITY_FILES: dict[RecordType, str] = {
    RecordType.COMPANY: "company.yaml",
    RecordType.ACCOUNT: "accounts.yaml",
    RecordType.CUSTOMER: "customers.yaml",
    RecordType.VENDOR: "vendors.yaml",
    RecordType.EMPLOYEE: "employees.yaml",
    RecordType.ITEM: "items.yaml",
    RecordType.INVOICE: "invoices.yaml",
    RecordType.SALES_RECEIPT: "sales_receipts.yaml",
    RecordType.CUSTOMER_PAYMENT: "customer_payments.yaml",
    RecordType.BILL: "bills.yaml",
    RecordType.BILL_PAYMENT: "bill_payments.yaml",
    RecordType.JOURNAL_ENTRY: "journal_entries.yaml",
    RecordType.PROJECT: "projects.yaml",
    RecordType.BANK_TRANSACTION: "bank_transactions.yaml",
    RecordType.ESTIMATE: "estimates.yaml",
    RecordType.TERMS: "terms.yaml",
    RecordType.PAYROLL_RUN: "payroll_runs.yaml",
}

RECORD_TYPES_BY_FILE = {path: record_type for record_type, path in ENTITY_FILES.items()}

REQUIRED_FIELDS: dict[RecordType, frozenset[str]] = {
    record_type: frozenset({"id"}) for record_type in ENTITY_FILES
}
REQUIRED_FIELDS.update(
    {
        RecordType.BILL: frozenset({"id", "vendor_id", "txn_date", "total_amount"}),
        RecordType.BILL_PAYMENT: frozenset({"id", "vendor_id", "txn_date", "amount"}),
        RecordType.INVOICE: frozenset({"id", "customer_id", "txn_date", "total_amount"}),
        RecordType.CUSTOMER_PAYMENT: frozenset({"id", "customer_id", "txn_date", "amount"}),
        RecordType.BANK_TRANSACTION: frozenset({"id", "date", "amount", "source_document_id"}),
        RecordType.JOURNAL_ENTRY: frozenset({"id", "txn_date", "lines", "purpose"}),
    }
)

GENERATOR_ONLY_FIELDS = frozenset(
    {
        "provenance_note",
        "sim_actor_id",
        "sim_event_ids",
        "sim_obligation_id",
        "sim_order_id",
        "sim_payment_id",
        "sim_product_id",
        "sim_project_id",
    }
)

