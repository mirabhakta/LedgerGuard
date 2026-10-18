#!/usr/bin/env python3
"""Render the Phase 0 sponsor dataset profile as Markdown."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


INTERPRETATIONS = {
    "accounts.yaml": "Chart of accounts; stable company-scoped account IDs and accounting classifications.",
    "bank_transactions.yaml": "Derived checking-account feed with signed cash movement, running balance, and source-document link.",
    "bill_payments.yaml": "Vendor payments applied to one or more bill documents (the supplied data uses one bill per payment).",
    "bills.yaml": "Accounts-payable vendor bills, due dates, item/account lines, costs, and obligation provenance.",
    "company.yaml": "Company profile, NAICS industry, address, and fiscal/opening metadata.",
    "customer_payments.yaml": "Customer receipts applied to invoices, including source/deposit accounts.",
    "customers.yaml": "Customer master records with terms, credit limits, relationship dates, and contact data.",
    "employees.yaml": "Employee master records with employment dates, job title, and gross weekly wage.",
    "estimates.yaml": "Project estimates/bids with amount and won/lost/open status.",
    "invoices.yaml": "Accounts-receivable invoices with due dates, line items, project links, and receivable obligations.",
    "items.yaml": "Product/service catalog with price, cost, and posting accounts.",
    "journal_entries.yaml": "Balanced general-ledger postings for wages, COGS, financing, depreciation, and other non-document events.",
    "manifest.yaml": "Per-company provenance, currency, generator configuration, content hashes, validation, and entity counts.",
    "payroll_runs.yaml": "Derived gross-only payroll runs linked to source journal entries.",
    "projects.yaml": "Project/job master data with customer, contract, dates, status history, changes, and reschedules.",
    "reports/ap_aging.yaml": "Accounts-payable aging snapshot; includes outstanding bill rows and aging buckets.",
    "reports/ar_aging.yaml": "Accounts-receivable aging snapshot; includes outstanding invoice rows and aging buckets.",
    "reports/balance_sheet.yaml": "Balance-sheet snapshot at period end plus quarter-end series.",
    "reports/profit_and_loss.yaml": "Full-period P&L plus monthly series.",
    "sales_receipts.yaml": "Point-of-sale/immediate-payment sales with line items and deposit account.",
    "terms.yaml": "Payment-term lookup (for example, due on receipt or Net 7).",
    "vendors.yaml": "Vendor master records with role, terms, relationship date, remittance address, and contacts.",
}

SAMPLE_FIELDS = {
    "accounts.yaml": ["id", "name", "classification", "account_type", "account_subtype"],
    "bank_transactions.yaml": ["id", "date", "amount", "direction", "source_document_id", "kind", "memo"],
    "bill_payments.yaml": ["id", "vendor_id", "vendor_name", "txn_date", "amount", "applications", "payment_account_id"],
    "bills.yaml": ["id", "doc_number", "vendor_id", "vendor_name", "txn_date", "due_date", "total_amount", "cost_category", "project_id"],
    "company.yaml": ["id", "legal_name", "trade_name", "industry_naics", "industry_title", "opening_date"],
    "customer_payments.yaml": ["id", "customer_id", "customer_name", "txn_date", "amount", "applications", "deposit_account_id"],
    "customers.yaml": ["id", "display_name", "payment_terms", "credit_limit_amount", "joined_date", "ended_date"],
    "employees.yaml": ["id", "display_name", "job_title", "hired_date", "released_date", "weekly_wage_amount"],
    "estimates.yaml": ["id", "date", "amount", "status", "project_id", "customer_id", "invoice_id"],
    "invoices.yaml": ["id", "doc_number", "customer_id", "customer_name", "txn_date", "due_date", "total_amount", "project_id", "memo"],
    "items.yaml": ["id", "name", "sku", "item_type", "unit_price_amount", "unit_cost_amount"],
    "journal_entries.yaml": ["id", "doc_number", "purpose", "txn_date", "project_id", "memo", "lines"],
    "manifest.yaml": ["schema_version", "realize_version", "dataset_id", "currency", "anchor_date", "content_hash", "entity_counts"],
    "payroll_runs.yaml": ["id", "date", "total_amount", "gross_only", "source_journal_entry_id", "lines"],
    "projects.yaml": ["id", "name", "customer_id", "project_kind", "contract_amount", "started_date", "planned_finish_date", "completed_date", "status"],
    "reports/ap_aging.yaml": ["report", "company", "period_end_date", "currency", "buckets", "total_outstanding", "rows"],
    "reports/ar_aging.yaml": ["report", "company", "period_end_date", "currency", "buckets", "total_outstanding", "rows"],
    "reports/balance_sheet.yaml": ["report", "company", "period_end_date", "currency", "period_end", "quarter_end"],
    "reports/profit_and_loss.yaml": ["report", "company", "period_start_date", "period_end_date", "currency", "full_period", "monthly"],
    "sales_receipts.yaml": ["id", "doc_number", "customer_id", "txn_date", "total_amount", "deposit_account_id", "memo"],
    "terms.yaml": ["id", "name", "days"],
    "vendors.yaml": ["id", "display_name", "payment_terms", "payment_terms_days", "supply_role", "joined_date"],
}


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def compact(value: Any) -> Any:
    if isinstance(value, list):
        if not value:
            return []
        return {"count_in_sampled_value": len(value), "first": compact(value[0])}
    if isinstance(value, dict):
        if len(value) <= 8:
            return {key: compact(item) for key, item in value.items()}
        keys = list(value)
        return {"keys": keys[:8], "additional_key_count": len(keys) - 8}
    return value


def sample_record(path: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        field: compact(record[field])
        for field in SAMPLE_FIELDS[path]
        if field in record
    }


def code(value: Any) -> str:
    return "`" + json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "`"


def render(profile: dict[str, Any], index_rows: list[dict[str, Any]]) -> str:
    families = profile["families"]
    row_records = sum(
        family["rows_total"] for family in families if family["shape"] == "record array"
    )
    lines: list[str] = []
    add = lines.append

    add("# LedgerGuard Phase 0 — Official QuickBooks Dataset Discovery Report")
    add("")
    add("**Status:** Phase 0 complete; no normalization, provider, policy, API, LangGraph, or scenario implementation has started.")
    add("")
    add("**Inspection date:** 2026-10-17 (America/Los_Angeles)")
    add("")
    add("## 1. Sources and integrity")
    add("")
    add("- Product source of truth: [LA Hacks 2026 — LedgerGuard / Agent Firewall Final Product & Technical Specification](https://docs.google.com/document/d/1kbs8MvBZYKtwyxwiX1skNhEmmC5sLictJwdaVNIWKHg/edit?usp=drivesdk). The Phase 0 work follows its execution-time firewall scope and does not begin System One integration.")
    add("- Dataset source of truth: [CL251215/QuickBooks-Hackathon-2026](https://huggingface.co/datasets/CL251215/QuickBooks-Hackathon-2026).")
    add("- Repository contents discovered through the Hugging Face repository API: `.gitattributes` (2,504 bytes) and `hackathon-100-participant.tar.gz` (26,675,707 bytes). There are no CSV, JSONL, Parquet, or Excel files at repository root.")
    add("- Downloaded archive SHA-256: `6090485212458315c6d58c2793221b79de54fa89191edccaeba2c5c1c5cb1f38`; this exactly matches the Hugging Face LFS object ID.")
    add(f"- Extracted archive: {profile['archive_file_count']:,} files, about 401 MB, containing {profile['world_count']} company worlds.")
    add(f"- Structured row arrays contain {row_records:,} records. In addition, the archive has 100 `index.json` rows, 100 manifests, and 400 report documents.")
    add("- Every one of the 100 copied `SCHEMA.md` files has the same SHA-256, so a single v4 schema governs all companies.")
    add("- The data README mentions optional `hidden/` simulation context, but this participant archive contains no `hidden/` directories. `index.json` counts 2,210 management decisions, 1,768 market-context entries, and 9,725 personas; those records are not shipped and cannot be used by LedgerGuard.")
    add("")
    add("## 2. Physical repository and archive layout")
    add("")
    add("```text")
    add("Hugging Face repository")
    add("├── .gitattributes")
    add("└── hackathon-100-participant.tar.gz")
    add("    └── hackathon-100/")
    add("        ├── DATA_README.md")
    add("        ├── index.json")
    add("        └── company-001/ ... company-100/")
    add("            └── rwm-v4/world-<dataset-id>/")
    add("                ├── SCHEMA.md")
    add("                ├── 18 top-level YAML files")
    add("                └── reports/ (4 YAML files)")
    add("```")
    add("")
    add("Each company contributes the same 23 files: 22 YAML files plus `SCHEMA.md`. With the two archive-level files, that is `100 × 23 + 2 = 2,302` files.")
    add("")
    add("## 3. Dataset-wide file inventory and row counts")
    add("")
    add("For row-oriented YAML, `rows` is the total number of records across all 100 files. For object-oriented YAML, each file is one document; aging reports also show the total number of embedded detail rows. `min / median / max` is the per-company record count.")
    add("")
    add("| Logical filename | Format / shape | Files | Total rows/documents | Non-empty files | Per-company min / median / max | Top-level columns | Accounting entity |")
    add("|---|---:|---:|---:|---:|---:|---:|---|")
    add(f"| `index.json` | JSON record array | 1 | {profile['index']['rows_total']:,} | 1 | n/a | {profile['index']['column_count']} | Cross-company catalog and headline financials |")
    for family in families:
        total = f"{family['rows_total']:,}"
        if family["embedded_rows_total"]:
            total += f" (+ {family['embedded_rows_total']:,} embedded rows)"
        add(
            f"| `{family['path']}` | YAML {family['shape']} | {family['files']} | {total} | "
            f"{family['files_nonempty']} | {family['rows_min']:,} / {family['rows_median']:,} / {family['rows_max']:,} | "
            f"{family['column_count']} | {INTERPRETATIONS[family['path']]} |"
        )
    add("| `DATA_README.md` | Markdown documentation | 1 | n/a | n/a | n/a | n/a | Dataset conventions, guarantees, limitations, and artifacts |")
    add("| `*/SCHEMA.md` | Markdown documentation | 100 identical copies | n/a | n/a | n/a | n/a | Realized World Model v4 field-level schema |")
    add("")
    add("The totals above exactly match the corresponding `entity_counts` sums in `index.json` for every shipped row-oriented entity.")
    add("")
    add("### Per-company physical-file row counts")
    add("")
    add("This matrix gives the row count for every physical row-oriented YAML file. The remaining five YAML files in each company (`manifest.yaml` and four reports) are document objects, so each has one top-level document; `SCHEMA.md` is documentation. Counts are sourced from `index.json`; their dataset-wide totals were cross-checked against the fully parsed files.")
    add("")
    count_columns = [
        ("company", "co"),
        ("accounts", "acct"),
        ("customers", "cust"),
        ("vendors", "vend"),
        ("employees", "emp"),
        ("items", "item"),
        ("invoices", "inv"),
        ("sales_receipts", "sale"),
        ("customer_payments", "c-pay"),
        ("bills", "bill"),
        ("bill_payments", "b-pay"),
        ("journal_entries", "JE"),
        ("projects", "proj"),
        ("bank_transactions", "bank"),
        ("estimates", "est"),
        ("terms", "term"),
        ("payroll_runs", "payroll"),
    ]
    add("| company | " + " | ".join(label for _key, label in count_columns) + " |")
    add("|---|" + "---:|" * len(count_columns))
    for row in index_rows:
        counts = row["entity_counts"]
        add(
            f"| `{row['company_id']}` | "
            + " | ".join(f"{counts[key]:,}" for key, _label in count_columns)
            + " |"
        )
    add("")
    add("Abbreviations: `co` company, `acct` accounts, `cust` customers, `vend` vendors, `emp` employees, `inv` invoices, `sale` sales receipts, `c-pay` customer payments, `b-pay` bill payments, `JE` journal entries, `proj` projects, `bank` bank transactions, `est` estimates.")
    add("")
    add("## 4. Columns, observed dtypes, null rates, and samples")
    add("")
    add("Dtypes and null rates below are measured from the full extracted dataset, not inferred from the schema document. Money remains a two-decimal YAML/JSON string by design. A list or object is reported as `array` or `object`; its nested structure is summarized separately in section 5. Null rate means explicit null or a missing top-level field divided by records for that logical file. Empty strings and empty arrays are not null.")
    add("")
    add("### `index.json`")
    add("")
    add("Cross-company index: 100 rows, 12 top-level columns.")
    add("")
    add("| Column | Observed dtype | Nulls | Null rate |")
    add("|---|---|---:|---:|")
    for column in profile["index"]["columns"]:
        add(f"| `{column['name']}` | `{column['dtype']}` | {column['null_count']}/{column['denominator']} | {pct(column['null_rate'])} |")
    add("")
    add("Three real sample rows (compact view):")
    add("")
    for sample in profile["index"]["samples"]:
        subset = {key: sample[key] for key in ["company_id", "display_name", "industry_naics", "industry_title", "profile", "size_tier", "business_status", "distressed"]}
        add(f"- {code(subset)}")
    add("")

    for family in families:
        add(f"### `{family['path']}`")
        add("")
        add(INTERPRETATIONS[family["path"]])
        add("")
        add("| Column | Observed dtype | Nulls | Null rate |")
        add("|---|---|---:|---:|")
        for column in family["columns"]:
            add(f"| `{column['name']}` | `{column['dtype']}` | {column['null_count']}/{column['denominator']} | {pct(column['null_rate'])} |")
        add("")
        add("Three real sample rows/documents (compact view; arrays show their count and first actual element):")
        add("")
        for sample in family["samples"]:
            value = sample_record(family["path"], sample["record"])
            add(f"- `{sample['company_id']}`: {code(value)}")
        add("")

    add("## 5. Nested structures in the v4 schema")
    add("")
    add("These are not additional top-level columns, but they are required to interpret the array/object columns above:")
    add("")
    add("| Nested structure | Fields observed/defined | Used by |")
    add("|---|---|---|")
    add("| `Address` | `line1`, `line2`, `city`, `state`, `postal_code`, `country` | company, customer, vendor |")
    add("| `DocumentLine` | `line_num`, `item_id`, `item_name`, `description`, `quantity`, `unit_price_amount`, `amount` | invoice, sales receipt, bill item lines |")
    add("| `AccountLine` | `line_num`, `account_id`, `account_name`, `description`, `amount` | bill account lines |")
    add("| `PaymentApplication` | `document_id`, `amount` | customer and bill payments |")
    add("| `JournalLine` | `line_num`, `account_id`, `account_name`, `description`, `debit_amount`, `credit_amount`, `customer_id`, `vendor_id`, `document_id` | journal entries |")
    add("| `PayrollLine` | `employee_id`, `employee_name`, `gross_amount` | payroll runs |")
    add("| `ChangeOrder` | `sim_day`, `date`, `amount` | projects |")
    add("| `Reschedule` | no nested fields observed because all 203 project `reschedules` arrays are empty in this archive | projects |")
    add("| `StatusChange` | `sim_day`, `date`, `status` | projects |")
    add("| Aging row | `document_id`, `party`, `due_date`, `days_past_due`, `bucket`, `balance` | AP/AR aging |")
    add("| Report series | full-period/monthly or period-end/quarter-end financial objects | P&L and balance sheet |")
    add("")
    add("Important schema conventions:")
    add("")
    add("- IDs and names are company-scoped. Canonical keys must include `company_id`; `cust-customer-3` can refer to different parties in different companies.")
    add("- `doc_number` is advisory and must not be a primary key.")
    add("- Amounts are decimal strings, not floating-point values. Normalization should use `Decimal`.")
    add("- Bank-feed amounts are signed: debit increases checking; credit decreases it.")
    add("- The observation/status date is the final simulation day. Bill/invoice paid/open status must be derived from applications and the chosen as-of date.")
    add("- `sim_*` and `provenance_note` fields are generator provenance. They are valuable for traceability and label construction but can leak simulation ground truth; keep them out of provider inputs and benchmark features unless explicitly justified.")
    add("")
    add("## 6. Required field coverage for LedgerGuard")
    add("")
    add("| Requested concept | Status | Real source and caveat |")
    add("|---|---|---|")
    add("| company ID | **present** | `index.json.company_id` and directory name; inject into every normalized key because entity IDs are company-scoped. `manifest.dataset_id` is a separate content/world ID. |")
    add("| transaction ID | **present** | Each transaction-like record has `id`; bank feed also has `source_document_id`. There is no universal field literally named `transaction_id`. |")
    add("| bill ID | **present** | `bills.id`; payment links use `applications[].document_id`. |")
    add("| invoice ID | **present** | `invoices.id`; receipt links use `applications[].document_id`; estimates may have `invoice_id`. |")
    add("| vendor | **present** | Vendor master plus `vendor_id` / `vendor_name` on bills and bill payments. |")
    add("| customer | **present** | Customer master plus `customer_id` / `customer_name` on sales and receipt entities. |")
    add("| description | **present** | Account/item descriptions and line-level descriptions; not every top-level transaction has a separate description. |")
    add("| memo | **present** | Present on bills, invoices, sales receipts, payments, journal entries, and bank transactions. |")
    add("| amount | **present** | `amount`, `total_amount`, line amounts, report balances. All are decimal strings except `index.json.financials_cents`, which uses integer cents. |")
    add("| date | **present** | Transaction entities use `txn_date` or `date`; bills/invoices also have `due_date`; master data has relationship dates. |")
    add("| currency | **present** | `manifest.currency` and report currency; it is company-level, not repeated on each source record. |")
    add("| category | **present, entity-specific** | `bills.cost_category`, `journal_entries.purpose`, `bank_transactions.kind`, account types/subtypes, and project/estimate kinds. There is no single universal category field. |")
    add("| account | **present** | Chart of accounts plus posting/source/deposit/payment/income account IDs and line account IDs. |")
    add("| status | **partial / derived** | Explicit on projects and estimates. Bill/invoice payment status is not stored directly; derive it from payment applications and the observation date/aging reports. |")
    add("| payment destination | **missing** | `payment_account_id` is the company's source account, not the vendor's bank destination. Any destination/change signal must be a disclosed synthetic extension. |")
    add("| payment method | **missing** | No check/ACH/card method field for bill payments or customer payments. |")
    add("| reference number | **present** | `doc_number` exists but is advisory; reliable links use entity `id`, `source_document_id`, and `applications[].document_id`. |")
    add("| transaction type | **present / derived** | File/entity type is authoritative; bank feed adds `kind`, journals add `purpose`, and bills add `expense_kind`. |")
    add("| business type / industry | **present** | `company.industry_naics`, `company.industry_title`, plus `index.profile` and `index.archetype`. |")
    add("")
    add("## 7. Recommended raw → canonical mapping")
    add("")
    add("The canonical layer should preserve actual records rather than force all accounting entities into a transaction-shaped row. The following mapping is safe for Phase 1:")
    add("")
    add("| Canonical field | Direct source | Rule / caveat |")
    add("|---|---|---|")
    add("| `record_id` | entity `id` | Make globally stable as `company_id:record_type:id`; never key on `doc_number`. |")
    add("| `company_id` | directory/index `company_id` | Required on every canonical record; not present inside most YAML rows. |")
    add("| `dataset_id` | `manifest.dataset_id` | Preserve as dataset-world provenance, separate from company ID. |")
    add("| `timestamp` | `txn_date` or `date` | Parse to a date/datetime. Master records should use their relevant relationship date or leave transaction timestamp unset. |")
    add("| `record_type` | logical filename/entity | Use a controlled enum: bill, bill_payment, invoice, customer_payment, sales_receipt, bank_transaction, journal_entry, etc. |")
    add("| `vendor_id`, `vendor_name` | bills/bill payments; vendor lookup | Direct for AP entities; null elsewhere. |")
    add("| `customer_id`, `customer_name` | invoices/receipts/payments; customer lookup | Direct for AR entities; null elsewhere. |")
    add("| `counterparty_id`, `counterparty_name` | vendor or customer fields | Derived alias based on record type; retain the typed vendor/customer fields too. |")
    add("| `description` | line description or account/item description | Do not overwrite `memo`; multiple line descriptions may require a list or deterministic concatenation. |")
    add("| `memo` | source `memo` | Direct where present, otherwise null. |")
    add("| `amount` | `total_amount` or `amount` | Convert with `Decimal`; preserve signed bank amounts. Journal entries should not invent a net amount (they balance to zero); keep lines and optionally derive total debits as a named feature. |")
    add("| `currency` | `manifest.currency` | Join by company/world. |")
    add("| `category` | cost category / journal purpose / bank kind | Keep the source-specific category and record which field supplied it. |")
    add("| `account_ids` | entity account fields and nested lines | Prefer a list/typed role map because one generic account loses debit/credit/source/deposit meaning. |")
    add("| `source_document_ids` | bank `source_document_id`; payment applications | Store as a list of typed references. Resolve each ID inside the same company. |")
    add("| `invoice_id`, `bill_id` | own record ID or resolved application/source link | Populate only after deterministic entity resolution, never by prefix alone if an exact company-scoped lookup is available. |")
    add("| `payment_id` | payment record `id` | Keep `sim_payment_id` only as provenance/label metadata, not as a production-facing identifier. |")
    add("| `status` | explicit status or derived payment state | Record `status_source` as `direct` or `derived_as_of`; do not pretend the source supplies bill/invoice status directly. |")
    add("| `source` | repository/archive/path/schema version | Example: `hf://CL251215/QuickBooks-Hackathon-2026@main/...`; include archive hash for reproducibility. |")
    add("| `raw_metadata` | untouched source row | Preserve nested lines and provenance so normalization is lossless. Restrict leakage-prone `sim_*` fields from inference views. |")
    add("")
    add("### Entity-to-LedgerGuard use")
    add("")
    add("| LedgerGuard need | Dataset entities | Feasibility |")
    add("|---|---|---|")
    add("| Vendor bill proposed actions | bills + vendors + accounts + AP aging | Strong: amount, due date, vendor, cost/account context, and outstanding balance are available. |")
    add("| Duplicate-obligation candidates | bills ↔ bill payments/applications; invoices ↔ customer payments/applications; bank source links; journal context | Strong for exact/document-linked candidates. Semantic near-duplicates must be injected as disclosed scenarios because the source books/feed are intentionally clean. |")
    add("| Vendor historical baseline | bills + bill payments + vendors | Strong for counts, amount statistics, timing, memo/cost/account history, and payment history. |")
    add("| Recent ledger history | bank transactions + journals + commercial documents | Strong, with deterministic date windows and company scoping. |")
    add("| Business context | company + index + manifest + accounts | Strong for industry/profile/currency/chart; no real user constraints. |")
    add("| `PAY_VENDOR_BILL` | bills + AP aging + bill payments | Directly supported for simulated proposed actions. |")
    add("| `POST_TRANSACTION` / `ADD_TRANSACTION` | bank transactions + journals + bills/invoices/sales receipts | Supported as runtime proposals derived from real records; execution remains simulated. |")
    add("| `MATCH_EXISTING` | document IDs, applications, bank source links, candidate similarity | Supported; exact matches are deterministic, semantic matching is a later provider judgment. |")
    add("")
    add("## 8. Fields that must remain optional or synthetic")
    add("")
    add("### Optional because real support is entity-dependent")
    add("")
    add("- `vendor`, `customer`, `counterparty`, `project_id`, `description`, `memo`, `category`, `account_ids`, `invoice_id`, `bill_id`, `payment_id`, and `status` must be optional or typed by record kind.")
    add("- `currency` is required after the manifest join but absent on raw transaction rows.")
    add("- Direct bill/invoice status is unavailable; a derived as-of status must carry provenance.")
    add("")
    add("### Disclosed synthetic extensions for LedgerGuard")
    add("")
    add("- Proposed-agent fields: `action_id`, `action_type`, `agent_goal`, `agent_reasoning_summary`, and proposed execution timestamp.")
    add("- Payment-destination fields: `previous_destination`, `new_destination`, destination fingerprint/account metadata, and change timestamp. The source dataset has no vendor bank destination.")
    add("- User policy fields: user constraints, approval limits, allowlists, or explicit goal constraints.")
    add("- Scenario/evaluation fields: scenario ID/type, source record IDs, exact modifications, modification reason, expected action, expected risk flags, and label provenance.")
    add("- Missing-context/business-purpose perturbations when the real memo/description is intentionally removed or made ambiguous.")
    add("")
    add("Synthetic extensions must never silently replace source values. Store them in a separate namespace/object and preserve `source_record_ids` plus the exact transformation.")
    add("")
    add("## 9. Phase 0 conclusions")
    add("")
    add("1. The official sponsor data is a 100-company, one-year, internally consistent synthetic accounting world in YAML RWM v4 format—not the guessed CSV layout.")
    add("2. The strongest LedgerGuard base is AP: bills, bill payments, vendors, accounts, bank links, and AP aging support realistic vendor-payment context and traceability.")
    add("3. Exact payment/document linkage is excellent; messy duplicates and unmatched bank-feed behavior are intentionally absent and therefore must be disclosed stress-test modifications.")
    add("4. Vendor payment destination and payment method are genuinely missing. A destination-change hero case must be a clearly labeled synthetic extension.")
    add("5. Company scope is mandatory for every key. Money should normalize to `Decimal`, and `doc_number` must never be used as identity.")
    add("6. Generator-only `sim_*` fields are useful for scenario lineage but risk label leakage. The Phase 1 model should preserve them in restricted raw metadata and exclude them from normal AccountingState/provider context.")
    add("7. Recommended next step, only after user confirmation: Phase 1 normalization and typed domain models built around the mappings above.")
    add("")
    add("## 10. Reproducibility notes")
    add("")
    add("- Local raw archive: `data/raw/hackathon-100-participant.tar.gz`")
    add("- Extracted raw tree: `data/raw/hackathon-100/`")
    add("- Phase 0 profiler: `tools/profile_quickbooks_dataset.rb`")
    add("- The profiler reads raw data only and does not normalize or mutate it.")
    add("")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_dataset_report.py PROFILE_JSON INDEX_JSON OUTPUT_MD")
    profile = json.loads(Path(sys.argv[1]).read_text())
    index_rows = json.loads(Path(sys.argv[2]).read_text())
    Path(sys.argv[3]).write_text(render(profile, index_rows), encoding="utf-8")


if __name__ == "__main__":
    main()
