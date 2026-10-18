# LedgerGuard Phase 0 — Official QuickBooks Dataset Discovery Report

**Status:** Phase 0 complete; the report now feeds the implemented Phase 1–7 normalization, provider, policy, LangGraph, scenario, and API pipeline.

**Inspection date:** 2026-10-17 (America/Los_Angeles)

## 1. Sources and integrity

- Product source of truth: [LA Hacks 2026 — LedgerGuard / Agent Firewall Final Product & Technical Specification](https://docs.google.com/document/d/1kbs8MvBZYKtwyxwiX1skNhEmmC5sLictJwdaVNIWKHg/edit?usp=drivesdk). The Phase 0 work follows its execution-time firewall scope and does not begin System One integration.
- Dataset source of truth: [CL251215/QuickBooks-Hackathon-2026](https://huggingface.co/datasets/CL251215/QuickBooks-Hackathon-2026).
- Repository contents discovered through the Hugging Face repository API: `.gitattributes` (2,504 bytes) and `hackathon-100-participant.tar.gz` (26,675,707 bytes). There are no CSV, JSONL, Parquet, or Excel files at repository root.
- Downloaded archive SHA-256: `6090485212458315c6d58c2793221b79de54fa89191edccaeba2c5c1c5cb1f38`; this exactly matches the Hugging Face LFS object ID.
- Extracted archive: 2,302 files, about 401 MB, containing 100 company worlds.
- Structured row arrays contain 758,823 records. In addition, the archive has 100 `index.json` rows, 100 manifests, and 400 report documents.
- Every one of the 100 copied `SCHEMA.md` files has the same SHA-256, so a single v4 schema governs all companies.
- The data README mentions optional `hidden/` simulation context, but this participant archive contains no `hidden/` directories. `index.json` counts 2,210 management decisions, 1,768 market-context entries, and 9,725 personas; those records are not shipped and cannot be used by LedgerGuard.

## 2. Physical repository and archive layout

```text
Hugging Face repository
├── .gitattributes
└── hackathon-100-participant.tar.gz
    └── hackathon-100/
        ├── DATA_README.md
        ├── index.json
        └── company-001/ ... company-100/
            └── rwm-v4/world-<dataset-id>/
                ├── SCHEMA.md
                ├── 18 top-level YAML files
                └── reports/ (4 YAML files)
```

Each company contributes the same 23 files: 22 YAML files plus `SCHEMA.md`. With the two archive-level files, that is `100 × 23 + 2 = 2,302` files.

## 3. Dataset-wide file inventory and row counts

For row-oriented YAML, `rows` is the total number of records across all 100 files. For object-oriented YAML, each file is one document; aging reports also show the total number of embedded detail rows. `min / median / max` is the per-company record count.

| Logical filename | Format / shape | Files | Total rows/documents | Non-empty files | Per-company min / median / max | Top-level columns | Accounting entity |
|---|---:|---:|---:|---:|---:|---:|---|
| `index.json` | JSON record array | 1 | 100 | 1 | n/a | 12 | Cross-company catalog and headline financials |
| `accounts.yaml` | YAML record array | 100 | 3,700 | 100 | 34 / 37 / 38 | 7 | Chart of accounts; stable company-scoped account IDs and accounting classifications. |
| `bank_transactions.yaml` | YAML record array | 100 | 234,610 | 100 | 39 / 1,021 / 14,266 | 10 | Derived checking-account feed with signed cash movement, running balance, and source-document link. |
| `bill_payments.yaml` | YAML record array | 100 | 36,032 | 100 | 25 / 226 / 4,928 | 13 | Vendor payments applied to one or more bill documents (the supplied data uses one bill per payment). |
| `bills.yaml` | YAML record array | 100 | 39,563 | 100 | 36 / 234 / 5,461 | 19 | Accounts-payable vendor bills, due dates, item/account lines, costs, and obligation provenance. |
| `company.yaml` | YAML record array | 100 | 100 | 100 | 1 / 1 / 1 | 14 | Company profile, NAICS industry, address, and fiscal/opening metadata. |
| `customer_payments.yaml` | YAML record array | 100 | 143,616 | 84 | 0 / 178 / 10,501 | 17 | Customer receipts applied to invoices, including source/deposit accounts. |
| `customers.yaml` | YAML record array | 100 | 8,322 | 100 | 1 / 20 / 1,526 | 19 | Customer master records with terms, credit limits, relationship dates, and contact data. |
| `employees.yaml` | YAML record array | 100 | 582 | 100 | 1 / 4 / 20 | 15 | Employee master records with employment dates, job title, and gross weekly wage. |
| `estimates.yaml` | YAML record array | 100 | 299 | 24 | 0 / 0 / 30 | 12 | Project estimates/bids with amount and won/lost/open status. |
| `invoices.yaml` | YAML record array | 100 | 84,451 | 86 | 0 / 197 / 5,551 | 21 | Accounts-receivable invoices with due dates, line items, project links, and receivable obligations. |
| `items.yaml` | YAML record array | 100 | 384 | 100 | 1 / 4 / 8 | 11 | Product/service catalog with price, cost, and posting accounts. |
| `journal_entries.yaml` | YAML record array | 100 | 151,730 | 100 | 107 / 952 / 6,822 | 12 | Balanced general-ledger postings for wages, COGS, financing, depreciation, and other non-document events. |
| `manifest.yaml` | YAML document object | 100 | 100 | 100 | 1 / 1 / 1 | 15 | Per-company provenance, currency, generator configuration, content hashes, validation, and entity counts. |
| `payroll_runs.yaml` | YAML record array | 100 | 25,733 | 100 | 4 / 235 / 1,020 | 8 | Derived gross-only payroll runs linked to source journal entries. |
| `projects.yaml` | YAML record array | 100 | 203 | 34 | 0 / 0 / 14 | 20 | Project/job master data with customer, contract, dates, status history, changes, and reschedules. |
| `reports/ap_aging.yaml` | YAML document object | 100 | 100 (+ 3,531 embedded rows) | 100 | 1 / 1 / 1 | 10 | Accounts-payable aging snapshot; includes outstanding bill rows and aging buckets. |
| `reports/ar_aging.yaml` | YAML document object | 100 | 100 (+ 9,531 embedded rows) | 100 | 1 / 1 / 1 | 10 | Accounts-receivable aging snapshot; includes outstanding invoice rows and aging buckets. |
| `reports/balance_sheet.yaml` | YAML document object | 100 | 100 | 100 | 1 / 1 / 1 | 9 | Balance-sheet snapshot at period end plus quarter-end series. |
| `reports/profit_and_loss.yaml` | YAML document object | 100 | 100 | 100 | 1 / 1 / 1 | 9 | Full-period P&L plus monthly series. |
| `sales_receipts.yaml` | YAML record array | 100 | 28,501 | 28 | 0 / 0 / 7,366 | 13 | Point-of-sale/immediate-payment sales with line items and deposit account. |
| `terms.yaml` | YAML record array | 100 | 176 | 100 | 1 / 2 / 3 | 4 | Payment-term lookup (for example, due on receipt or Net 7). |
| `vendors.yaml` | YAML record array | 100 | 821 | 100 | 3 / 8 / 17 | 15 | Vendor master records with role, terms, relationship date, remittance address, and contacts. |
| `DATA_README.md` | Markdown documentation | 1 | n/a | n/a | n/a | n/a | Dataset conventions, guarantees, limitations, and artifacts |
| `*/SCHEMA.md` | Markdown documentation | 100 identical copies | n/a | n/a | n/a | n/a | Realized World Model v4 field-level schema |

The totals above exactly match the corresponding `entity_counts` sums in `index.json` for every shipped row-oriented entity.

### Per-company physical-file row counts

This matrix gives the row count for every physical row-oriented YAML file. The remaining five YAML files in each company (`manifest.yaml` and four reports) are document objects, so each has one top-level document; `SCHEMA.md` is documentation. Counts are sourced from `index.json`; their dataset-wide totals were cross-checked against the fully parsed files.

| company | co | acct | cust | vend | emp | item | inv | sale | c-pay | bill | b-pay | JE | proj | bank | est | term | payroll |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `company-001` | 1 | 37 | 40 | 7 | 7 | 6 | 1,574 | 0 | 3,046 | 359 | 344 | 2,006 | 0 | 3,606 | 0 | 2 | 212 |
| `company-002` | 1 | 37 | 81 | 7 | 10 | 4 | 3,163 | 0 | 6,057 | 349 | 340 | 3,820 | 0 | 6,725 | 0 | 2 | 323 |
| `company-003` | 1 | 37 | 136 | 8 | 17 | 5 | 5,132 | 0 | 9,813 | 377 | 367 | 6,513 | 0 | 10,734 | 0 | 2 | 542 |
| `company-004` | 1 | 37 | 50 | 8 | 5 | 5 | 1,913 | 0 | 3,664 | 358 | 349 | 2,321 | 0 | 4,217 | 0 | 2 | 200 |
| `company-005` | 1 | 37 | 75 | 10 | 8 | 5 | 3,079 | 0 | 5,847 | 370 | 360 | 3,860 | 0 | 6,506 | 0 | 2 | 283 |
| `company-006` | 1 | 37 | 167 | 9 | 17 | 6 | 5,315 | 0 | 8,730 | 234 | 229 | 6,822 | 0 | 9,534 | 0 | 3 | 572 |
| `company-007` | 1 | 37 | 41 | 8 | 6 | 6 | 1,372 | 0 | 2,224 | 226 | 218 | 2,141 | 0 | 2,653 | 0 | 3 | 204 |
| `company-008` | 1 | 37 | 82 | 8 | 10 | 6 | 2,899 | 0 | 4,888 | 231 | 224 | 3,859 | 0 | 5,454 | 0 | 3 | 338 |
| `company-009` | 1 | 37 | 143 | 10 | 19 | 4 | 4,883 | 0 | 8,033 | 230 | 222 | 6,498 | 0 | 8,832 | 0 | 3 | 574 |
| `company-010` | 1 | 37 | 44 | 9 | 6 | 1 | 1,579 | 0 | 2,591 | 1,804 | 1,644 | 2,318 | 0 | 4,451 | 0 | 3 | 206 |
| `company-011` | 1 | 37 | 83 | 10 | 12 | 4 | 2,784 | 0 | 4,644 | 3,021 | 2,715 | 3,858 | 0 | 7,719 | 0 | 3 | 357 |
| `company-012` | 1 | 37 | 150 | 9 | 17 | 1 | 5,238 | 0 | 8,788 | 5,461 | 4,928 | 6,690 | 0 | 14,266 | 0 | 3 | 545 |
| `company-013` | 1 | 37 | 37 | 7 | 6 | 1 | 1,608 | 0 | 2,709 | 211 | 206 | 2,355 | 0 | 3,120 | 0 | 3 | 191 |
| `company-014` | 1 | 37 | 71 | 8 | 9 | 5 | 2,296 | 0 | 3,785 | 233 | 223 | 3,311 | 0 | 4,341 | 0 | 3 | 329 |
| `company-015` | 1 | 37 | 156 | 8 | 16 | 6 | 5,058 | 0 | 8,353 | 234 | 226 | 6,383 | 0 | 9,066 | 0 | 3 | 481 |
| `company-016` | 1 | 37 | 39 | 10 | 5 | 1 | 1,593 | 0 | 2,644 | 1,821 | 1,659 | 2,225 | 0 | 4,480 | 0 | 3 | 166 |
| `company-017` | 1 | 37 | 77 | 10 | 13 | 4 | 3,093 | 0 | 5,236 | 3,330 | 2,987 | 4,189 | 0 | 8,597 | 0 | 3 | 367 |
| `company-018` | 1 | 37 | 157 | 9 | 16 | 6 | 5,551 | 0 | 10,501 | 416 | 403 | 6,756 | 0 | 11,474 | 0 | 2 | 564 |
| `company-019` | 1 | 37 | 40 | 8 | 6 | 4 | 1,622 | 0 | 3,125 | 333 | 322 | 2,171 | 0 | 3,675 | 0 | 2 | 213 |
| `company-020` | 1 | 37 | 76 | 8 | 14 | 1 | 2,960 | 0 | 5,577 | 333 | 326 | 4,121 | 0 | 6,351 | 0 | 2 | 433 |
| `company-021` | 1 | 37 | 177 | 8 | 18 | 6 | 5,447 | 0 | 10,408 | 415 | 402 | 6,689 | 0 | 11,397 | 0 | 2 | 577 |
| `company-022` | 1 | 37 | 29 | 7 | 1 | 1 | 27 | 0 | 0 | 82 | 26 | 435 | 0 | 39 | 0 | 2 | 4 |
| `company-023` | 1 | 37 | 6 | 13 | 1 | 7 | 18 | 0 | 55 | 382 | 336 | 143 | 6 | 445 | 0 | 1 | 47 |
| `company-024` | 1 | 37 | 10 | 13 | 3 | 7 | 32 | 0 | 81 | 625 | 578 | 174 | 10 | 716 | 0 | 1 | 47 |
| `company-025` | 1 | 37 | 14 | 13 | 4 | 7 | 43 | 0 | 95 | 785 | 673 | 204 | 14 | 829 | 0 | 1 | 47 |
| `company-026` | 1 | 37 | 4 | 12 | 2 | 6 | 13 | 0 | 26 | 419 | 386 | 131 | 4 | 464 | 0 | 1 | 47 |
| `company-027` | 1 | 37 | 5 | 15 | 2 | 6 | 15 | 0 | 29 | 610 | 534 | 1,479 | 5 | 804 | 24 | 1 | 235 |
| `company-028` | 1 | 37 | 10 | 15 | 2 | 7 | 35 | 0 | 84 | 842 | 748 | 2,027 | 10 | 1,078 | 30 | 1 | 235 |
| `company-029` | 1 | 37 | 5 | 17 | 1 | 7 | 19 | 0 | 45 | 553 | 512 | 1,233 | 5 | 809 | 20 | 1 | 235 |
| `company-030` | 1 | 37 | 7 | 16 | 1 | 7 | 19 | 0 | 53 | 596 | 550 | 1,463 | 7 | 845 | 22 | 1 | 235 |
| `company-031` | 1 | 37 | 13 | 12 | 4 | 7 | 36 | 0 | 95 | 611 | 567 | 185 | 13 | 722 | 14 | 1 | 47 |
| `company-032` | 1 | 37 | 6 | 11 | 1 | 7 | 16 | 0 | 53 | 282 | 256 | 138 | 6 | 362 | 9 | 1 | 47 |
| `company-033` | 1 | 37 | 8 | 12 | 2 | 6 | 27 | 0 | 64 | 576 | 506 | 163 | 8 | 625 | 12 | 1 | 47 |
| `company-034` | 1 | 37 | 6 | 12 | 4 | 7 | 21 | 0 | 45 | 465 | 418 | 154 | 6 | 519 | 12 | 1 | 49 |
| `company-035` | 1 | 37 | 4 | 13 | 1 | 7 | 16 | 0 | 40 | 407 | 363 | 138 | 4 | 455 | 5 | 1 | 47 |
| `company-036` | 1 | 37 | 4 | 12 | 3 | 6 | 11 | 0 | 24 | 381 | 333 | 129 | 4 | 409 | 6 | 1 | 48 |
| `company-037` | 1 | 37 | 3 | 13 | 4 | 6 | 11 | 0 | 21 | 358 | 316 | 1,535 | 3 | 579 | 8 | 1 | 238 |
| `company-038` | 1 | 37 | 4 | 14 | 1 | 7 | 18 | 0 | 38 | 386 | 346 | 903 | 4 | 624 | 7 | 1 | 235 |
| `company-039` | 1 | 37 | 4 | 15 | 2 | 7 | 17 | 0 | 41 | 383 | 344 | 1,446 | 4 | 626 | 10 | 1 | 236 |
| `company-040` | 1 | 37 | 7 | 14 | 4 | 7 | 21 | 0 | 59 | 601 | 560 | 1,904 | 7 | 864 | 14 | 1 | 237 |
| `company-041` | 1 | 37 | 4 | 14 | 1 | 7 | 8 | 0 | 18 | 320 | 285 | 1,042 | 4 | 542 | 11 | 1 | 235 |
| `company-042` | 1 | 37 | 7 | 13 | 2 | 7 | 22 | 0 | 56 | 502 | 433 | 152 | 7 | 544 | 14 | 1 | 47 |
| `company-043` | 1 | 37 | 14 | 13 | 4 | 7 | 42 | 0 | 117 | 749 | 657 | 201 | 14 | 835 | 0 | 1 | 47 |
| `company-044` | 1 | 37 | 2 | 12 | 1 | 6 | 7 | 0 | 0 | 388 | 264 | 203 | 2 | 392 | 0 | 1 | 35 |
| `company-045` | 1 | 38 | 14 | 13 | 3 | 8 | 214 | 0 | 407 | 451 | 425 | 451 | 6 | 943 | 0 | 2 | 102 |
| `company-046` | 1 | 38 | 21 | 13 | 6 | 7 | 373 | 0 | 717 | 535 | 489 | 952 | 4 | 1,360 | 0 | 2 | 139 |
| `company-047` | 1 | 38 | 37 | 14 | 7 | 8 | 863 | 0 | 1,703 | 549 | 516 | 1,533 | 5 | 2,419 | 0 | 2 | 182 |
| `company-048` | 1 | 38 | 14 | 14 | 4 | 8 | 252 | 0 | 484 | 473 | 445 | 756 | 7 | 1,049 | 0 | 2 | 107 |
| `company-049` | 1 | 38 | 19 | 11 | 3 | 8 | 478 | 0 | 926 | 343 | 328 | 1,377 | 4 | 1,589 | 14 | 2 | 323 |
| `company-050` | 1 | 38 | 31 | 13 | 5 | 8 | 1,103 | 0 | 2,145 | 388 | 375 | 2,092 | 4 | 2,936 | 13 | 2 | 408 |
| `company-051` | 1 | 38 | 14 | 14 | 3 | 8 | 218 | 0 | 417 | 429 | 406 | 1,240 | 5 | 1,130 | 10 | 2 | 291 |
| `company-052` | 1 | 38 | 16 | 13 | 5 | 7 | 507 | 0 | 973 | 505 | 474 | 1,590 | 4 | 1,799 | 8 | 2 | 337 |
| `company-053` | 1 | 38 | 29 | 13 | 6 | 8 | 1,199 | 0 | 2,289 | 462 | 424 | 2,217 | 4 | 3,103 | 10 | 2 | 382 |
| `company-054` | 1 | 38 | 12 | 13 | 5 | 8 | 279 | 0 | 524 | 426 | 394 | 1,315 | 5 | 1,240 | 11 | 2 | 303 |
| `company-055` | 1 | 38 | 15 | 12 | 4 | 8 | 450 | 0 | 855 | 473 | 455 | 1,609 | 4 | 1,644 | 7 | 2 | 321 |
| `company-056` | 1 | 38 | 37 | 11 | 6 | 7 | 1,174 | 0 | 2,258 | 424 | 395 | 2,300 | 4 | 3,072 | 8 | 2 | 403 |
| `company-057` | 1 | 37 | 12 | 4 | 1 | 1 | 156 | 0 | 147 | 40 | 36 | 108 | 0 | 239 | 0 | 2 | 51 |
| `company-058` | 1 | 37 | 34 | 4 | 3 | 1 | 353 | 0 | 324 | 40 | 36 | 310 | 0 | 514 | 0 | 2 | 153 |
| `company-059` | 1 | 37 | 64 | 4 | 6 | 1 | 742 | 0 | 686 | 40 | 36 | 623 | 0 | 1,033 | 0 | 2 | 306 |
| `company-060` | 1 | 37 | 12 | 4 | 1 | 1 | 156 | 0 | 150 | 40 | 36 | 107 | 0 | 241 | 0 | 2 | 51 |
| `company-061` | 1 | 37 | 30 | 4 | 3 | 1 | 363 | 0 | 337 | 40 | 36 | 310 | 0 | 527 | 0 | 2 | 153 |
| `company-062` | 1 | 37 | 52 | 4 | 6 | 1 | 553 | 0 | 519 | 40 | 36 | 623 | 0 | 866 | 0 | 2 | 306 |
| `company-063` | 1 | 37 | 21 | 4 | 1 | 1 | 178 | 0 | 164 | 40 | 36 | 108 | 0 | 256 | 0 | 2 | 51 |
| `company-064` | 1 | 37 | 18 | 4 | 2 | 1 | 198 | 0 | 189 | 40 | 36 | 211 | 0 | 332 | 0 | 2 | 102 |
| `company-065` | 1 | 37 | 61 | 4 | 4 | 1 | 526 | 0 | 515 | 40 | 36 | 417 | 0 | 760 | 0 | 2 | 204 |
| `company-066` | 1 | 37 | 12 | 4 | 1 | 1 | 126 | 0 | 121 | 40 | 36 | 108 | 0 | 213 | 0 | 2 | 51 |
| `company-067` | 1 | 37 | 20 | 4 | 2 | 1 | 256 | 0 | 247 | 40 | 36 | 211 | 0 | 390 | 0 | 2 | 102 |
| `company-068` | 1 | 37 | 44 | 4 | 4 | 1 | 558 | 0 | 545 | 40 | 36 | 417 | 0 | 790 | 0 | 2 | 204 |
| `company-069` | 1 | 37 | 15 | 4 | 2 | 1 | 75 | 0 | 60 | 40 | 36 | 210 | 0 | 202 | 0 | 2 | 102 |
| `company-070` | 1 | 37 | 30 | 4 | 4 | 1 | 138 | 0 | 112 | 40 | 36 | 417 | 0 | 357 | 0 | 2 | 204 |
| `company-071` | 1 | 37 | 78 | 4 | 8 | 1 | 348 | 0 | 279 | 40 | 36 | 829 | 0 | 728 | 0 | 2 | 408 |
| `company-072` | 1 | 37 | 19 | 3 | 2 | 1 | 83 | 0 | 68 | 36 | 31 | 190 | 0 | 185 | 0 | 2 | 85 |
| `company-073` | 1 | 37 | 1 | 5 | 2 | 1 | 0 | 626 | 0 | 92 | 85 | 575 | 0 | 817 | 0 | 1 | 102 |
| `company-074` | 1 | 37 | 1 | 5 | 5 | 1 | 0 | 626 | 0 | 92 | 85 | 884 | 0 | 970 | 0 | 1 | 255 |
| `company-075` | 1 | 37 | 1 | 5 | 11 | 1 | 0 | 626 | 0 | 92 | 85 | 1,502 | 0 | 1,276 | 0 | 1 | 561 |
| `company-076` | 1 | 37 | 1 | 5 | 2 | 1 | 0 | 628 | 0 | 90 | 84 | 571 | 0 | 813 | 0 | 1 | 102 |
| `company-077` | 1 | 37 | 1 | 5 | 5 | 1 | 0 | 626 | 0 | 90 | 84 | 881 | 0 | 966 | 0 | 1 | 255 |
| `company-078` | 1 | 37 | 1 | 5 | 20 | 1 | 0 | 626 | 0 | 92 | 85 | 2,429 | 0 | 1,735 | 0 | 1 | 1,020 |
| `company-079` | 1 | 37 | 1 | 5 | 6 | 1 | 0 | 626 | 0 | 92 | 85 | 987 | 0 | 1,021 | 0 | 1 | 306 |
| `company-080` | 1 | 37 | 1 | 5 | 12 | 1 | 0 | 626 | 0 | 92 | 85 | 1,604 | 0 | 1,326 | 0 | 1 | 612 |
| `company-081` | 1 | 37 | 1 | 5 | 20 | 1 | 0 | 626 | 0 | 92 | 85 | 2,429 | 0 | 1,735 | 0 | 1 | 1,020 |
| `company-082` | 1 | 37 | 1 | 5 | 6 | 1 | 0 | 626 | 0 | 92 | 85 | 983 | 0 | 1,017 | 0 | 1 | 306 |
| `company-083` | 1 | 37 | 1 | 5 | 4 | 1 | 0 | 732 | 0 | 92 | 83 | 833 | 0 | 1,022 | 0 | 1 | 204 |
| `company-084` | 1 | 37 | 1 | 5 | 8 | 1 | 0 | 732 | 0 | 92 | 83 | 1,245 | 0 | 1,226 | 0 | 1 | 408 |
| `company-085` | 1 | 37 | 1 | 5 | 2 | 1 | 0 | 732 | 0 | 92 | 83 | 627 | 0 | 920 | 0 | 1 | 102 |
| `company-086` | 1 | 37 | 1 | 5 | 4 | 1 | 0 | 732 | 0 | 92 | 83 | 833 | 0 | 1,022 | 0 | 1 | 204 |
| `company-087` | 1 | 37 | 421 | 3 | 3 | 1 | 222 | 577 | 211 | 36 | 33 | 310 | 0 | 975 | 0 | 2 | 153 |
| `company-088` | 1 | 37 | 746 | 4 | 6 | 1 | 533 | 1,193 | 494 | 39 | 35 | 619 | 0 | 2,029 | 0 | 2 | 306 |
| `company-089` | 1 | 37 | 1,526 | 4 | 13 | 1 | 943 | 2,158 | 899 | 40 | 36 | 1,344 | 0 | 3,761 | 0 | 2 | 663 |
| `company-090` | 1 | 37 | 421 | 3 | 3 | 1 | 240 | 621 | 227 | 36 | 28 | 310 | 0 | 1,030 | 0 | 2 | 153 |
| `company-091` | 1 | 37 | 114 | 4 | 5 | 2 | 506 | 26 | 457 | 40 | 36 | 518 | 0 | 777 | 0 | 2 | 255 |
| `company-092` | 1 | 37 | 222 | 4 | 11 | 2 | 828 | 77 | 774 | 39 | 36 | 1,134 | 0 | 1,449 | 0 | 2 | 561 |
| `company-093` | 1 | 37 | 69 | 4 | 2 | 2 | 197 | 38 | 178 | 38 | 33 | 205 | 0 | 350 | 0 | 2 | 100 |
| `company-094` | 1 | 37 | 504 | 4 | 5 | 1 | 165 | 3,573 | 160 | 40 | 36 | 519 | 0 | 4,028 | 0 | 2 | 255 |
| `company-095` | 1 | 37 | 1,008 | 4 | 11 | 1 | 210 | 7,366 | 206 | 40 | 36 | 1,138 | 0 | 8,174 | 0 | 2 | 561 |
| `company-096` | 1 | 37 | 260 | 4 | 2 | 1 | 28 | 1,946 | 27 | 40 | 36 | 207 | 0 | 2,112 | 0 | 2 | 102 |
| `company-097` | 1 | 34 | 23 | 4 | 2 | 3 | 2 | 293 | 5 | 37 | 32 | 207 | 0 | 433 | 0 | 2 | 102 |
| `company-098` | 1 | 34 | 44 | 4 | 4 | 3 | 3 | 533 | 7 | 37 | 34 | 413 | 0 | 779 | 0 | 2 | 204 |
| `company-099` | 1 | 34 | 57 | 4 | 11 | 3 | 1 | 713 | 4 | 37 | 34 | 1,134 | 0 | 1,313 | 0 | 2 | 561 |
| `company-100` | 1 | 34 | 14 | 4 | 2 | 3 | 1 | 197 | 4 | 37 | 25 | 170 | 0 | 292 | 0 | 2 | 65 |

Abbreviations: `co` company, `acct` accounts, `cust` customers, `vend` vendors, `emp` employees, `inv` invoices, `sale` sales receipts, `c-pay` customer payments, `b-pay` bill payments, `JE` journal entries, `proj` projects, `bank` bank transactions, `est` estimates.

## 4. Columns, observed dtypes, null rates, and samples

Dtypes and null rates below are measured from the full extracted dataset, not inferred from the schema document. Money remains a two-decimal YAML/JSON string by design. A list or object is reported as `array` or `object`; its nested structure is summarized separately in section 5. Null rate means explicit null or a missing top-level field divided by records for that logical file. Empty strings and empty arrays are not null.

### `index.json`

Cross-company index: 100 rows, 12 top-level columns.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `archetype` | `string` | 0/100 | 0.00% |
| `business_status` | `string` | 0/100 | 0.00% |
| `company_id` | `string` | 0/100 | 0.00% |
| `dataset_id` | `string` | 0/100 | 0.00% |
| `display_name` | `string` | 0/100 | 0.00% |
| `distressed` | `boolean` | 0/100 | 0.00% |
| `entity_counts` | `object` | 0/100 | 0.00% |
| `financials_cents` | `object` | 0/100 | 0.00% |
| `industry_naics` | `string` | 0/100 | 0.00% |
| `industry_title` | `string` | 0/100 | 0.00% |
| `profile` | `string` | 0/100 | 0.00% |
| `size_tier` | `string` | 0/100 | 0.00% |

Three real sample rows (compact view):

- `{"company_id":"company-001","display_name":"Hearthloaf Bakeries","industry_naics":"311812","industry_title":"Commercial Bakeries","profile":"wholesale","size_tier":"small","business_status":"open","distressed":false}`
- `{"company_id":"company-002","display_name":"Roastline Coffee Roasters","industry_naics":"311920","industry_title":"Coffee and Tea Manufacturing","profile":"wholesale","size_tier":"medium","business_status":"open","distressed":false}`
- `{"company_id":"company-003","display_name":"Keghouse Brewing Co","industry_naics":"312120","industry_title":"Breweries","profile":"wholesale","size_tier":"large","business_status":"open","distressed":false}`

### `accounts.yaml`

Chart of accounts; stable company-scoped account IDs and accounting classifications.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `account_subtype` | `string` | 0/3700 | 0.00% |
| `account_type` | `string` | 0/3700 | 0.00% |
| `classification` | `string` | 0/3700 | 0.00% |
| `description` | `string` | 0/3700 | 0.00% |
| `id` | `string` | 0/3700 | 0.00% |
| `name` | `string` | 0/3700 | 0.00% |
| `sim_event_ids` | `array` | 0/3700 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"acct-checking","name":"Business Checking","classification":"asset","account_type":"bank","account_subtype":"checking"}`
- `company-001`: `{"id":"acct-receivable","name":"Accounts Receivable","classification":"asset","account_type":"accounts_receivable","account_subtype":"accounts_receivable"}`
- `company-001`: `{"id":"acct-inventory","name":"Inventory Asset","classification":"asset","account_type":"other_current_asset","account_subtype":"inventory"}`

### `bank_transactions.yaml`

Derived checking-account feed with signed cash movement, running balance, and source-document link.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `amount` | `string` | 0/234610 | 0.00% |
| `date` | `string` | 0/234610 | 0.00% |
| `direction` | `string` | 0/234610 | 0.00% |
| `id` | `string` | 0/234610 | 0.00% |
| `kind` | `string` | 0/234610 | 0.00% |
| `memo` | `string` | 0/234610 | 0.00% |
| `running_balance_amount` | `string` | 0/234610 | 0.00% |
| `sim_day` | `integer` | 0/234610 | 0.00% |
| `sim_event_ids` | `array` | 0/234610 | 0.00% |
| `source_document_id` | `string` | 0/234610 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"bank-000001","date":"2025-10-06","amount":"115191.26","direction":"debit","source_document_id":"je-open-00001","kind":"opening_equity","memo":"Owner's opening contribution"}`
- `company-001`: `{"id":"bank-000002","date":"2025-10-14","amount":"-750.00","direction":"credit","source_document_id":"je-wagepay-00001","kind":"wage_payment","memo":"Wages paid"}`
- `company-001`: `{"id":"bank-000003","date":"2025-10-15","amount":"-500.00","direction":"credit","source_document_id":"bpay-00002","kind":"bill_payment","memo":"Vendor bill paid"}`

### `bill_payments.yaml`

Vendor payments applied to one or more bill documents (the supplied data uses one bill per payment).

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `amount` | `string` | 0/36032 | 0.00% |
| `applications` | `array` | 0/36032 | 0.00% |
| `id` | `string` | 0/36032 | 0.00% |
| `memo` | `string` | 0/36032 | 0.00% |
| `payment_account_id` | `string` | 0/36032 | 0.00% |
| `provenance_note` | `string` | 0/36032 | 0.00% |
| `sim_event_ids` | `array` | 0/36032 | 0.00% |
| `sim_obligation_id` | `string` | 0/36032 | 0.00% |
| `sim_payment_id` | `string` | 0/36032 | 0.00% |
| `txn_date` | `string` | 0/36032 | 0.00% |
| `txn_sim_day` | `integer` | 0/36032 | 0.00% |
| `vendor_id` | `string` | 0/36032 | 0.00% |
| `vendor_name` | `string` | 0/36032 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"bpay-00002","vendor_id":"vend-landlord","vendor_name":"Granite Bay Commercial Properties","txn_date":"2025-10-15","amount":"500.00","applications":{"count_in_sampled_value":1,"first":{"document_id":"bill-operating-00003","amount":"500.00"}},"payment_account_id":"acct-checking"}`
- `company-001`: `{"id":"bpay-00008","vendor_id":"vend-supplier","vendor_name":"Ironclad Larkspur Outfitters","txn_date":"2025-10-20","amount":"4098.00","applications":{"count_in_sampled_value":1,"first":{"document_id":"bill-00005","amount":"4098.00"}},"payment_account_id":"acct-checking"}`
- `company-001`: `{"id":"bpay-00012","vendor_id":"vend-water","vendor_name":"Jasper Mill Municipal Utilities","txn_date":"2025-10-21","amount":"3.00","applications":{"count_in_sampled_value":1,"first":{"document_id":"bill-utilities-00015","amount":"3.00"}},"payment_account_id":"acct-checking"}`

### `bills.yaml`

Accounts-payable vendor bills, due dates, item/account lines, costs, and obligation provenance.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `account_lines` | `array` | 0/39563 | 0.00% |
| `cost_category` | `string` | 0/39563 | 0.00% |
| `doc_number` | `string` | 0/39563 | 0.00% |
| `due_date` | `string` | 0/39563 | 0.00% |
| `due_sim_day` | `integer` | 0/39563 | 0.00% |
| `expense_kind` | `string` | 0/39563 | 0.00% |
| `id` | `string` | 0/39563 | 0.00% |
| `item_lines` | `array` | 0/39563 | 0.00% |
| `memo` | `string` | 0/39563 | 0.00% |
| `project_id` | `null | string` | 28235/39563 | 71.37% |
| `provenance_note` | `string` | 0/39563 | 0.00% |
| `sim_event_ids` | `array` | 0/39563 | 0.00% |
| `sim_obligation_id` | `string` | 0/39563 | 0.00% |
| `sim_order_id` | `null | string` | 37474/39563 | 94.72% |
| `total_amount` | `string` | 0/39563 | 0.00% |
| `txn_date` | `string` | 0/39563 | 0.00% |
| `txn_sim_day` | `integer` | 0/39563 | 0.00% |
| `vendor_id` | `string` | 0/39563 | 0.00% |
| `vendor_name` | `string` | 0/39563 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"bill-00005","doc_number":"BILL-5001","vendor_id":"vend-supplier","vendor_name":"Ironclad Larkspur Outfitters","txn_date":"2025-10-10","due_date":"2025-10-17","total_amount":"4098.00","cost_category":"purchase","project_id":null}`
- `company-001`: `{"id":"bill-operating-00003","doc_number":"BILL-5002","vendor_id":"vend-landlord","vendor_name":"Granite Bay Commercial Properties","txn_date":"2025-10-13","due_date":"2025-10-13","total_amount":"500.00","cost_category":"operating","project_id":null}`
- `company-001`: `{"id":"bill-00034","doc_number":"BILL-5003","vendor_id":"vend-supplier","vendor_name":"Ironclad Larkspur Outfitters","txn_date":"2025-10-15","due_date":"2025-10-22","total_amount":"10367.94","cost_category":"purchase","project_id":null}`

### `company.yaml`

Company profile, NAICS industry, address, and fiscal/opening metadata.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `address` | `object` | 0/100 | 0.00% |
| `email` | `string` | 0/100 | 0.00% |
| `fiscal_year_start_month` | `integer` | 0/100 | 0.00% |
| `id` | `string` | 0/100 | 0.00% |
| `industry_naics` | `string` | 0/100 | 0.00% |
| `industry_title` | `string` | 0/100 | 0.00% |
| `legal_name` | `string` | 0/100 | 0.00% |
| `opening_date` | `string` | 0/100 | 0.00% |
| `opening_sim_day` | `integer` | 0/100 | 0.00% |
| `phone` | `string` | 0/100 | 0.00% |
| `sim_actor_id` | `string` | 0/100 | 0.00% |
| `sim_event_ids` | `array` | 0/100 | 0.00% |
| `trade_name` | `string` | 0/100 | 0.00% |
| `website` | `string` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"company-main","legal_name":"Hearthloaf Bakeries LLC","trade_name":"Hearthloaf Bakeries","industry_naics":"311812","industry_title":"Commercial Bakeries","opening_date":"2025-10-06"}`
- `company-002`: `{"id":"company-main","legal_name":"Roastline Coffee Roasters LLC","trade_name":"Roastline Coffee Roasters","industry_naics":"311920","industry_title":"Coffee and Tea Manufacturing","opening_date":"2025-10-06"}`
- `company-003`: `{"id":"company-main","legal_name":"Keghouse Brewing Co LLC","trade_name":"Keghouse Brewing Co","industry_naics":"312120","industry_title":"Breweries","opening_date":"2025-10-06"}`

### `customer_payments.yaml`

Customer receipts applied to invoices, including source/deposit accounts.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `amount` | `string` | 0/143616 | 0.00% |
| `applications` | `array` | 0/143616 | 0.00% |
| `customer_id` | `string` | 0/143616 | 0.00% |
| `customer_name` | `string` | 0/143616 | 0.00% |
| `deposit_account_id` | `string` | 0/143616 | 0.00% |
| `id` | `string` | 0/143616 | 0.00% |
| `memo` | `string` | 0/143616 | 0.00% |
| `project_id` | `null | string` | 142244/143616 | 99.04% |
| `provenance_note` | `string` | 0/143616 | 0.00% |
| `settles` | `string` | 0/143616 | 0.00% |
| `sim_event_ids` | `array` | 0/143616 | 0.00% |
| `sim_obligation_id` | `string` | 0/143616 | 0.00% |
| `sim_payment_id` | `string` | 0/143616 | 0.00% |
| `source_account_id` | `string` | 0/143616 | 0.00% |
| `txn_date` | `string` | 0/143616 | 0.00% |
| `txn_sim_day` | `integer` | 0/143616 | 0.00% |
| `unapplied_amount` | `string` | 0/143616 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"rcpt-00003","customer_id":"cust-customer-20","customer_name":"Meridian Millbrook Movers","txn_date":"2025-10-16","amount":"223.56","applications":{"count_in_sampled_value":1,"first":{"document_id":"inv-00023","amount":"223.56"}},"deposit_account_id":"acct-checking"}`
- `company-001`: `{"id":"rcpt-00004","customer_id":"cust-customer-7","customer_name":"Pioneer Oakhurst Supply","txn_date":"2025-10-17","amount":"337.63","applications":{"count_in_sampled_value":1,"first":{"document_id":"inv-00024","amount":"337.63"}},"deposit_account_id":"acct-checking"}`
- `company-001`: `{"id":"rcpt-00006","customer_id":"cust-customer-6","customer_name":"Okonkwo & Daughters Warehousing","txn_date":"2025-10-17","amount":"429.97","applications":{"count_in_sampled_value":1,"first":{"document_id":"inv-00021","amount":"429.97"}},"deposit_account_id":"acct-checking"}`

### `customers.yaml`

Customer master records with terms, credit limits, relationship dates, and contact data.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `address` | `object` | 0/8322 | 0.00% |
| `company_name` | `string` | 0/8322 | 0.00% |
| `contact_family_name` | `string` | 0/8322 | 0.00% |
| `contact_given_name` | `string` | 0/8322 | 0.00% |
| `credit_limit_amount` | `string` | 0/8322 | 0.00% |
| `display_name` | `string` | 0/8322 | 0.00% |
| `email` | `string` | 0/8322 | 0.00% |
| `ended_date` | `null | string` | 6995/8322 | 84.05% |
| `ended_sim_day` | `integer | null` | 6995/8322 | 84.05% |
| `ended_sim_event_id` | `null | string` | 7711/8322 | 92.66% |
| `id` | `string` | 0/8322 | 0.00% |
| `joined_date` | `string` | 0/8322 | 0.00% |
| `joined_sim_day` | `integer` | 0/8322 | 0.00% |
| `notes` | `string` | 0/8322 | 0.00% |
| `payment_terms` | `string` | 0/8322 | 0.00% |
| `payment_terms_days` | `integer` | 0/8322 | 0.00% |
| `phone` | `string` | 0/8322 | 0.00% |
| `sim_actor_id` | `string` | 0/8322 | 0.00% |
| `sim_event_ids` | `array` | 0/8322 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"cust-customer-1","display_name":"Yarrow Field Florals & Co.","payment_terms":"Net 7","credit_limit_amount":"3431.44","joined_date":"2025-10-06","ended_date":null}`
- `company-001`: `{"id":"cust-customer-10","display_name":"Farrow & Daughters Toyworks","payment_terms":"Net 7","credit_limit_amount":"2160.45","joined_date":"2025-10-06","ended_date":"2026-01-26"}`
- `company-001`: `{"id":"cust-customer-11","display_name":"Ashford Confections","payment_terms":"Net 7","credit_limit_amount":"3272.74","joined_date":"2025-10-06","ended_date":null}`

### `employees.yaml`

Employee master records with employment dates, job title, and gross weekly wage.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `display_name` | `string` | 0/582 | 0.00% |
| `email` | `string` | 0/582 | 0.00% |
| `family_name` | `string` | 0/582 | 0.00% |
| `given_name` | `string` | 0/582 | 0.00% |
| `hired_date` | `string` | 0/582 | 0.00% |
| `hired_sim_day` | `integer` | 0/582 | 0.00% |
| `id` | `string` | 0/582 | 0.00% |
| `job_title` | `string` | 0/582 | 0.00% |
| `phone` | `string` | 0/582 | 0.00% |
| `released_date` | `null | string` | 490/582 | 84.19% |
| `released_sim_day` | `integer | null` | 490/582 | 84.19% |
| `released_sim_event_id` | `null | string` | 490/582 | 84.19% |
| `sim_actor_id` | `string` | 0/582 | 0.00% |
| `sim_event_ids` | `array` | 0/582 | 0.00% |
| `weekly_wage_amount` | `string` | 0/582 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"emp-employee-1","display_name":"Viktor Duvall","job_title":"Order Picker","hired_date":"2025-10-06","released_date":null,"weekly_wage_amount":"750.00"}`
- `company-001`: `{"id":"emp-employee-2","display_name":"Rosalind Karlsen","job_title":"Fulfillment Associate","hired_date":"2025-11-03","released_date":null,"weekly_wage_amount":"750.00"}`
- `company-001`: `{"id":"emp-employee-3","display_name":"Uma Yeboah","job_title":"Inventory Clerk","hired_date":"2025-11-03","released_date":null,"weekly_wage_amount":"750.00"}`

### `estimates.yaml`

Project estimates/bids with amount and won/lost/open status.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `amount` | `string` | 0/299 | 0.00% |
| `customer_id` | `null | string` | 168/299 | 56.19% |
| `customer_name` | `null | string` | 168/299 | 56.19% |
| `date` | `string` | 0/299 | 0.00% |
| `id` | `string` | 0/299 | 0.00% |
| `invoice_id` | `null | string` | 182/299 | 60.87% |
| `project_id` | `null | string` | 168/299 | 56.19% |
| `project_kind` | `string` | 0/299 | 0.00% |
| `provenance_note` | `string` | 0/299 | 0.00% |
| `sim_day` | `integer` | 0/299 | 0.00% |
| `sim_event_ids` | `array` | 0/299 | 0.00% |
| `status` | `string` | 0/299 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-027`: `{"id":"est-00007","date":"2025-10-06","amount":"29578.75","status":"lost","project_id":null,"customer_id":null,"invoice_id":null}`
- `company-027`: `{"id":"est-00094","date":"2025-10-21","amount":"604853.69","status":"won","project_id":"proj-00001","customer_id":"cust-client-1","invoice_id":"minv-00001"}`
- `company-027`: `{"id":"est-00129","date":"2025-10-27","amount":"503152.63","status":"lost","project_id":null,"customer_id":null,"invoice_id":null}`

### `invoices.yaml`

Accounts-receivable invoices with due dates, line items, project links, and receivable obligations.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `customer_id` | `string` | 0/84451 | 0.00% |
| `customer_name` | `string` | 0/84451 | 0.00% |
| `deposit_account_id` | `null | string` | 84175/84451 | 99.67% |
| `deposit_applied_amount` | `string` | 0/84451 | 0.00% |
| `doc_number` | `string` | 0/84451 | 0.00% |
| `due_date` | `string` | 0/84451 | 0.00% |
| `due_sim_day` | `integer` | 0/84451 | 0.00% |
| `id` | `string` | 0/84451 | 0.00% |
| `income_account_id` | `string` | 0/84451 | 0.00% |
| `lines` | `array` | 0/84451 | 0.00% |
| `memo` | `string` | 0/84451 | 0.00% |
| `project_id` | `null | string` | 83823/84451 | 99.26% |
| `provenance_note` | `string` | 0/84451 | 0.00% |
| `retainage_account_id` | `null | string` | 83823/84451 | 99.26% |
| `retainage_amount` | `string` | 0/84451 | 0.00% |
| `sim_event_ids` | `array` | 0/84451 | 0.00% |
| `sim_obligation_id` | `string` | 0/84451 | 0.00% |
| `sim_order_id` | `null | string` | 9316/84451 | 11.03% |
| `total_amount` | `string` | 0/84451 | 0.00% |
| `txn_date` | `string` | 0/84451 | 0.00% |
| `txn_sim_day` | `integer` | 0/84451 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"inv-00021","doc_number":"INV-1001","customer_id":"cust-customer-6","customer_name":"Okonkwo & Daughters Warehousing","txn_date":"2025-10-13","due_date":"2025-10-20","total_amount":"472.50","project_id":null,"memo":"Thank you for your order."}`
- `company-001`: `{"id":"inv-00022","doc_number":"INV-1002","customer_id":"cust-customer-13","customer_name":"Union Thornbury Stationers","txn_date":"2025-10-13","due_date":"2025-10-20","total_amount":"189.00","project_id":null,"memo":"Thank you for your order."}`
- `company-001`: `{"id":"inv-00023","doc_number":"INV-1003","customer_id":"cust-customer-20","customer_name":"Meridian Millbrook Movers","txn_date":"2025-10-14","due_date":"2025-10-21","total_amount":"310.50","project_id":null,"memo":"Order shipped complete from our warehouse."}`

### `items.yaml`

Product/service catalog with price, cost, and posting accounts.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `description` | `string` | 0/384 | 0.00% |
| `id` | `string` | 0/384 | 0.00% |
| `income_account_id` | `string` | 0/384 | 0.00% |
| `item_type` | `string` | 0/384 | 0.00% |
| `name` | `string` | 0/384 | 0.00% |
| `purchase_account_id` | `string` | 0/384 | 0.00% |
| `sim_event_ids` | `array` | 0/384 | 0.00% |
| `sim_product_id` | `null | string` | 284/384 | 73.96% |
| `sku` | `string` | 0/384 | 0.00% |
| `unit_cost_amount` | `string` | 0/384 | 0.00% |
| `unit_price_amount` | `string` | 0/384 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"item-00001","name":"Hamburger Bun Flat, 8 ct","sku":"HBF-08-122","item_type":"non_inventory","unit_price_amount":"13.50","unit_cost_amount":"6.83"}`
- `company-001`: `{"id":"item-00002","name":"Croissant Tray, 24 ct","sku":"CRT-24-327","item_type":"non_inventory","unit_price_amount":"16.20","unit_cost_amount":"8.53"}`
- `company-001`: `{"id":"item-00003","name":"Pan Loaf Bread Case, White","sku":"PLB-WH-767","item_type":"non_inventory","unit_price_amount":"18.90","unit_cost_amount":"10.24"}`

### `journal_entries.yaml`

Balanced general-ledger postings for wages, COGS, financing, depreciation, and other non-document events.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `doc_number` | `string` | 0/151730 | 0.00% |
| `id` | `string` | 0/151730 | 0.00% |
| `lines` | `array` | 0/151730 | 0.00% |
| `memo` | `string` | 0/151730 | 0.00% |
| `project_id` | `null | string` | 146597/151730 | 96.62% |
| `provenance_note` | `string` | 0/151730 | 0.00% |
| `purpose` | `string` | 0/151730 | 0.00% |
| `sim_event_ids` | `array` | 0/151730 | 0.00% |
| `sim_obligation_id` | `null | string` | 24116/151730 | 15.89% |
| `sim_payment_id` | `null | string` | 130788/151730 | 86.20% |
| `txn_date` | `string` | 0/151730 | 0.00% |
| `txn_sim_day` | `integer` | 0/151730 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"je-open-00001","doc_number":"JE-9001","purpose":"opening_equity","txn_date":"2025-10-06","project_id":null,"memo":"Owner's opening cash contribution.","lines":{"count_in_sampled_value":1,"first":{"keys":["line_num","account_id","account_name","description","debit_amount","credit_amount","customer_id","vendor_id"],"additional_key_count":1}}}`
- `company-001`: `{"id":"je-cogs-00137","doc_number":"JE-9002","purpose":"cost_of_goods","txn_date":"2025-10-13","project_id":null,"memo":"Cost of 35 units delivered.","lines":{"count_in_sampled_value":1,"first":{"keys":["line_num","account_id","account_name","description","debit_amount","credit_amount","customer_id","vendor_id"],"additional_key_count":1}}}`
- `company-001`: `{"id":"je-cogs-00139","doc_number":"JE-9003","purpose":"cost_of_goods","txn_date":"2025-10-13","project_id":null,"memo":"Cost of 14 units delivered.","lines":{"count_in_sampled_value":1,"first":{"keys":["line_num","account_id","account_name","description","debit_amount","credit_amount","customer_id","vendor_id"],"additional_key_count":1}}}`

### `manifest.yaml`

Per-company provenance, currency, generator configuration, content hashes, validation, and entity counts.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `anchor_date` | `string` | 0/100 | 0.00% |
| `content_hash` | `string` | 0/100 | 0.00% |
| `currency` | `string` | 0/100 | 0.00% |
| `dataset_id` | `string` | 0/100 | 0.00% |
| `entity_counts` | `object` | 0/100 | 0.00% |
| `identity` | `object` | 0/100 | 0.00% |
| `input_reference` | `string` | 0/100 | 0.00% |
| `name_seed` | `integer` | 0/100 | 0.00% |
| `pool_fingerprint` | `string` | 0/100 | 0.00% |
| `pool_versions` | `object` | 0/100 | 0.00% |
| `realize_version` | `string` | 0/100 | 0.00% |
| `schema_version` | `string` | 0/100 | 0.00% |
| `sim` | `object` | 0/100 | 0.00% |
| `unrealized_actor_roles` | `array` | 0/100 | 0.00% |
| `validation` | `object` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"schema_version":"4","realize_version":"6","dataset_id":"world-a0bb0d826496e79a","currency":"USD","anchor_date":"2025-10-06","content_hash":"56bb84c9cc2a834fd03edcda768b0656","entity_counts":{"keys":["accounts","bank_transactions","bill_payments","bills","company","customer_payments","customers","employees"],"additional_key_count":12}}`
- `company-002`: `{"schema_version":"4","realize_version":"6","dataset_id":"world-fc6550b583dde063","currency":"USD","anchor_date":"2025-10-06","content_hash":"15349b6497cdc28afecd05f7d8f63960","entity_counts":{"keys":["accounts","bank_transactions","bill_payments","bills","company","customer_payments","customers","employees"],"additional_key_count":12}}`
- `company-003`: `{"schema_version":"4","realize_version":"6","dataset_id":"world-05d64e2d010225ca","currency":"USD","anchor_date":"2025-10-06","content_hash":"1f32f3b48ddcee5ba59d6887b10b53f8","entity_counts":{"keys":["accounts","bank_transactions","bill_payments","bills","company","customer_payments","customers","employees"],"additional_key_count":12}}`

### `payroll_runs.yaml`

Derived gross-only payroll runs linked to source journal entries.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `date` | `string` | 0/25733 | 0.00% |
| `gross_only` | `boolean` | 0/25733 | 0.00% |
| `id` | `string` | 0/25733 | 0.00% |
| `lines` | `array` | 0/25733 | 0.00% |
| `sim_day` | `integer` | 0/25733 | 0.00% |
| `sim_event_ids` | `array` | 0/25733 | 0.00% |
| `source_journal_entry_id` | `string` | 0/25733 | 0.00% |
| `total_amount` | `string` | 0/25733 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"payrun-wagepay-00001","date":"2025-10-14","total_amount":"750.00","gross_only":true,"source_journal_entry_id":"je-wagepay-00001","lines":{"count_in_sampled_value":1,"first":{"employee_id":"emp-employee-1","employee_name":"Viktor Duvall","gross_amount":"750.00"}}}`
- `company-001`: `{"id":"payrun-wagepay-00014","date":"2025-10-23","total_amount":"750.00","gross_only":true,"source_journal_entry_id":"je-wagepay-00014","lines":{"count_in_sampled_value":1,"first":{"employee_id":"emp-employee-1","employee_name":"Viktor Duvall","gross_amount":"750.00"}}}`
- `company-001`: `{"id":"payrun-wagepay-00037","date":"2025-10-30","total_amount":"750.00","gross_only":true,"source_journal_entry_id":"je-wagepay-00037","lines":{"count_in_sampled_value":1,"first":{"employee_id":"emp-employee-1","employee_name":"Viktor Duvall","gross_amount":"750.00"}}}`

### `projects.yaml`

Project/job master data with customer, contract, dates, status history, changes, and reschedules.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `change_orders` | `array` | 0/203 | 0.00% |
| `completed_date` | `null | string` | 79/203 | 38.92% |
| `completed_sim_day` | `integer | null` | 79/203 | 38.92% |
| `contract_amount` | `string` | 0/203 | 0.00% |
| `customer_id` | `string` | 0/203 | 0.00% |
| `customer_name` | `string` | 0/203 | 0.00% |
| `id` | `string` | 0/203 | 0.00% |
| `name` | `string` | 0/203 | 0.00% |
| `original_contract_amount` | `string` | 0/203 | 0.00% |
| `planned_finish_date` | `string` | 0/203 | 0.00% |
| `planned_finish_sim_day` | `integer` | 0/203 | 0.00% |
| `project_kind` | `string` | 0/203 | 0.00% |
| `provenance_note` | `string` | 0/203 | 0.00% |
| `reschedules` | `array` | 0/203 | 0.00% |
| `sim_event_ids` | `array` | 0/203 | 0.00% |
| `sim_project_id` | `string` | 0/203 | 0.00% |
| `started_date` | `string` | 0/203 | 0.00% |
| `started_sim_day` | `integer` | 0/203 | 0.00% |
| `status` | `string` | 0/203 | 0.00% |
| `status_history` | `array` | 0/203 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-023`: `{"id":"proj-00001","name":"Documentary project for Yarrow Field Orchards Inc.","customer_id":"cust-client-1","project_kind":"documentary project","contract_amount":"133277.63","started_date":"2025-10-06","planned_finish_date":"2026-02-11","completed_date":"2026-03-17","status":"completed"}`
- `company-023`: `{"id":"proj-00002","name":"Promotional video for Glenmoor Grocers","customer_id":"cust-client-2","project_kind":"promotional video","contract_amount":"29755.47","started_date":"2025-11-03","planned_finish_date":"2025-12-27","completed_date":"2026-01-08","status":"completed"}`
- `company-023`: `{"id":"proj-00003","name":"Promotional video for Lanternwood Lantern Stationers Holdings","customer_id":"cust-client-3","project_kind":"promotional video","contract_amount":"27000.00","started_date":"2026-01-26","planned_finish_date":"2026-03-20","completed_date":"2026-04-07","status":"completed"}`

### `reports/ap_aging.yaml`

Accounts-payable aging snapshot; includes outstanding bill rows and aging buckets.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `buckets` | `object` | 0/100 | 0.00% |
| `company` | `string` | 0/100 | 0.00% |
| `currency` | `string` | 0/100 | 0.00% |
| `generated_from` | `string` | 0/100 | 0.00% |
| `period` | `string` | 0/100 | 0.00% |
| `period_end_date` | `string` | 0/100 | 0.00% |
| `period_start_date` | `string` | 0/100 | 0.00% |
| `report` | `string` | 0/100 | 0.00% |
| `rows` | `array` | 0/100 | 0.00% |
| `total_outstanding` | `string` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"report":"Accounts Payable Aging","company":"Hearthloaf Bakeries","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"20932.95","1-30":"6066.30","31-60":"0.00","61-90":"0.00","90+":"0.00"},"total_outstanding":"26999.25","rows":{"count_in_sampled_value":1,"first":{"document_id":"bill-01798","party":"Ironclad Larkspur Outfitters","due_date":"2026-10-04","days_past_due":2,"bucket":"1-30","balance":"1923.76"}}}`
- `company-002`: `{"report":"Accounts Payable Aging","company":"Roastline Coffee Roasters","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"30527.70","1-30":"589.95","31-60":"0.00","61-90":"0.00","90+":"0.00"},"total_outstanding":"31117.65","rows":{"count_in_sampled_value":1,"first":{"document_id":"bill-operating-03809","party":"Hollyhock Commercial Properties","due_date":"2026-10-05","days_past_due":1,"bucket":"1-30","balance":"500.00"}}}`
- `company-003`: `{"report":"Accounts Payable Aging","company":"Keghouse Brewing Co","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"42478.69","1-30":"710.18","31-60":"0.00","61-90":"0.00","90+":"0.00"},"total_outstanding":"43188.87","rows":{"count_in_sampled_value":1,"first":{"document_id":"bill-operating-06007","party":"Ironbridge Realty Partners","due_date":"2026-10-05","days_past_due":1,"bucket":"1-30","balance":"500.00"}}}`

### `reports/ar_aging.yaml`

Accounts-receivable aging snapshot; includes outstanding invoice rows and aging buckets.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `buckets` | `object` | 0/100 | 0.00% |
| `company` | `string` | 0/100 | 0.00% |
| `currency` | `string` | 0/100 | 0.00% |
| `generated_from` | `string` | 0/100 | 0.00% |
| `period` | `string` | 0/100 | 0.00% |
| `period_end_date` | `string` | 0/100 | 0.00% |
| `period_start_date` | `string` | 0/100 | 0.00% |
| `report` | `string` | 0/100 | 0.00% |
| `rows` | `array` | 0/100 | 0.00% |
| `total_outstanding` | `string` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"report":"Accounts Receivable Aging","company":"Hearthloaf Bakeries","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"21030.50","1-30":"4322.27","31-60":"776.10","61-90":"0.00","90+":"0.00"},"total_outstanding":"26128.87","rows":{"count_in_sampled_value":1,"first":{"document_id":"inv-01524","party":"Gallagher Apothecary Company","due_date":"2026-08-14","days_past_due":53,"bucket":"31-60","balance":"776.10"}}}`
- `company-002`: `{"report":"Accounts Receivable Aging","company":"Roastline Coffee Roasters","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"27309.96","1-30":"19559.55","31-60":"3733.24","61-90":"1336.80","90+":"148.41"},"total_outstanding":"52087.96","rows":{"count_in_sampled_value":1,"first":{"document_id":"inv-02377","party":"Dovetail Inlet Cove Works","due_date":"2026-06-19","days_past_due":109,"bucket":"90+","balance":"148.41"}}}`
- `company-003`: `{"report":"Accounts Receivable Aging","company":"Keghouse Brewing Co","period_end_date":"2026-10-06","currency":"USD","buckets":{"current":"58532.69","1-30":"39112.39","31-60":"2890.11","61-90":"1265.30","90+":"1907.02"},"total_outstanding":"103707.51","rows":{"count_in_sampled_value":1,"first":{"document_id":"inv-03591","party":"Keystone Bellrock Provisions","due_date":"2026-05-14","days_past_due":145,"bucket":"90+","balance":"184.07"}}}`

### `reports/balance_sheet.yaml`

Balance-sheet snapshot at period end plus quarter-end series.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `company` | `string` | 0/100 | 0.00% |
| `currency` | `string` | 0/100 | 0.00% |
| `generated_from` | `string` | 0/100 | 0.00% |
| `period` | `string` | 0/100 | 0.00% |
| `period_end` | `object` | 0/100 | 0.00% |
| `period_end_date` | `string` | 0/100 | 0.00% |
| `period_start_date` | `string` | 0/100 | 0.00% |
| `quarter_end` | `array` | 0/100 | 0.00% |
| `report` | `string` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"report":"Balance Sheet","company":"Hearthloaf Bakeries","period_end_date":"2026-10-06","currency":"USD","period_end":{"as_of_sim_day":365,"as_of_date":"2026-10-06","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"104107.55"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-payable","name":"Accounts Payable","amount":"26999.25"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"115191.26"}}},"total_assets":"142132.72","total_liabilities":"29999.25","total_equity":"112133.47","total_liabilities_and_equity":"142132.72","balances":true},"quarter_end":{"count_in_sampled_value":1,"first":{"as_of_sim_day":86,"as_of_date":"2025-12-31","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"113159.74"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-payable","name":"Accounts Payable","amount":"10227.24"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"115191.26"}}},"total_assets":"152986.59","total_liabilities":"10977.24","total_equity":"142009.35","total_liabilities_and_equity":"152986.59","balances":true}}}`
- `company-002`: `{"report":"Balance Sheet","company":"Roastline Coffee Roasters","period_end_date":"2026-10-06","currency":"USD","period_end":{"as_of_sim_day":365,"as_of_date":"2026-10-06","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"96080.62"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-payable","name":"Accounts Payable","amount":"31117.65"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"173816.28"}}},"total_assets":"167409.68","total_liabilities":"34867.65","total_equity":"132542.03","total_liabilities_and_equity":"167409.68","balances":true},"quarter_end":{"count_in_sampled_value":1,"first":{"as_of_sim_day":86,"as_of_date":"2025-12-31","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"134234.98"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-payable","name":"Accounts Payable","amount":"31144.52"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"173816.28"}}},"total_assets":"221227.24","total_liabilities":"32644.52","total_equity":"188582.72","total_liabilities_and_equity":"221227.24","balances":true}}}`
- `company-003`: `{"report":"Balance Sheet","company":"Keghouse Brewing Co","period_end_date":"2026-10-06","currency":"USD","period_end":{"as_of_sim_day":365,"as_of_date":"2026-10-06","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"152717.19"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-accrued-interest","name":"Accrued Interest","amount":"42.50"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"374434.54"}}},"total_assets":"300695.76","total_liabilities":"78152.89","total_equity":"222542.87","total_liabilities_and_equity":"300695.76","balances":true},"quarter_end":{"count_in_sampled_value":1,"first":{"as_of_sim_day":86,"as_of_date":"2025-12-31","sections":{"Assets":{"count_in_sampled_value":1,"first":{"account_id":"acct-checking","name":"Business Checking","amount":"297787.45"}},"Liabilities":{"count_in_sampled_value":1,"first":{"account_id":"acct-payable","name":"Accounts Payable","amount":"20751.92"}},"Equity":{"count_in_sampled_value":1,"first":{"account_id":"acct-opening-equity","name":"Opening Balance Equity","amount":"374434.54"}}},"total_assets":"399116.69","total_liabilities":"20751.92","total_equity":"378364.77","total_liabilities_and_equity":"399116.69","balances":true}}}`

### `reports/profit_and_loss.yaml`

Full-period P&L plus monthly series.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `company` | `string` | 0/100 | 0.00% |
| `currency` | `string` | 0/100 | 0.00% |
| `full_period` | `object` | 0/100 | 0.00% |
| `generated_from` | `string` | 0/100 | 0.00% |
| `monthly` | `array` | 0/100 | 0.00% |
| `period` | `string` | 0/100 | 0.00% |
| `period_end_date` | `string` | 0/100 | 0.00% |
| `period_start_date` | `string` | 0/100 | 0.00% |
| `report` | `string` | 0/100 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"report":"Profit and Loss","company":"Hearthloaf Bakeries","period_start_date":"2025-10-06","period_end_date":"2026-10-06","currency":"USD","full_period":{"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"809717.76"}},"net_profit":"90544.13"},"monthly":{"count_in_sampled_value":1,"first":{"month_end_sim_day":25,"month_end_date":"2025-10-31","full_calendar_month":false,"days_covered":26,"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"12001.50"}},"net_profit":"1498.87"}}}`
- `company-002`: `{"report":"Profit and Loss","company":"Roastline Coffee Roasters","period_start_date":"2025-10-06","period_end_date":"2026-10-06","currency":"USD","full_period":{"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"1157894.23"}},"net_profit":"70053.47"},"monthly":{"count_in_sampled_value":1,"first":{"month_end_sim_day":25,"month_end_date":"2025-10-31","full_calendar_month":false,"days_covered":26,"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"19167.25"}},"net_profit":"1121.88"}}}`
- `company-003`: `{"report":"Profit and Loss","company":"Keghouse Brewing Co","period_start_date":"2025-10-06","period_end_date":"2026-10-06","currency":"USD","full_period":{"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"1895102.43"}},"net_profit":"9413.37"},"monthly":{"count_in_sampled_value":1,"first":{"month_end_sim_day":25,"month_end_date":"2025-10-31","full_calendar_month":false,"days_covered":26,"lines":{"count_in_sampled_value":1,"first":{"section":"Income","line":"Revenue","amount":"37953.80"}},"net_profit":"753.93"}}}`

### `sales_receipts.yaml`

Point-of-sale/immediate-payment sales with line items and deposit account.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `customer_id` | `string` | 0/28501 | 0.00% |
| `customer_name` | `string` | 0/28501 | 0.00% |
| `deposit_account_id` | `string` | 0/28501 | 0.00% |
| `doc_number` | `string` | 0/28501 | 0.00% |
| `id` | `string` | 0/28501 | 0.00% |
| `income_account_id` | `string` | 0/28501 | 0.00% |
| `lines` | `array` | 0/28501 | 0.00% |
| `memo` | `string` | 0/28501 | 0.00% |
| `provenance_note` | `string` | 0/28501 | 0.00% |
| `sim_event_ids` | `array` | 0/28501 | 0.00% |
| `total_amount` | `string` | 0/28501 | 0.00% |
| `txn_date` | `string` | 0/28501 | 0.00% |
| `txn_sim_day` | `integer` | 0/28501 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-073`: `{"id":"srcpt-card-0000","doc_number":"SR-3001","customer_id":"cust-walk-in","txn_date":"2025-10-06","total_amount":"655.84","deposit_account_id":"acct-undeposited-funds","memo":"Register takings, card."}`
- `company-073`: `{"id":"srcpt-cash-0000","doc_number":"SR-3002","customer_id":"cust-walk-in","txn_date":"2025-10-06","total_amount":"267.88","deposit_account_id":"acct-checking","memo":"Register takings, cash."}`
- `company-073`: `{"id":"srcpt-card-0002","doc_number":"SR-3003","customer_id":"cust-walk-in","txn_date":"2025-10-08","total_amount":"649.27","deposit_account_id":"acct-undeposited-funds","memo":"Register takings, card."}`

### `terms.yaml`

Payment-term lookup (for example, due on receipt or Net 7).

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `days` | `integer` | 0/176 | 0.00% |
| `id` | `string` | 0/176 | 0.00% |
| `name` | `string` | 0/176 | 0.00% |
| `sim_event_ids` | `array` | 0/176 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"terms-net-0","name":"Due on receipt","days":0}`
- `company-001`: `{"id":"terms-net-7","name":"Net 7","days":7}`
- `company-002`: `{"id":"terms-net-0","name":"Due on receipt","days":0}`

### `vendors.yaml`

Vendor master records with role, terms, relationship date, remittance address, and contacts.

| Column | Observed dtype | Nulls | Null rate |
|---|---|---:|---:|
| `address` | `object` | 0/821 | 0.00% |
| `company_name` | `string` | 0/821 | 0.00% |
| `contact_family_name` | `string` | 0/821 | 0.00% |
| `contact_given_name` | `string` | 0/821 | 0.00% |
| `display_name` | `string` | 0/821 | 0.00% |
| `email` | `string` | 0/821 | 0.00% |
| `id` | `string` | 0/821 | 0.00% |
| `joined_date` | `string` | 0/821 | 0.00% |
| `joined_sim_day` | `integer` | 0/821 | 0.00% |
| `payment_terms` | `string` | 0/821 | 0.00% |
| `payment_terms_days` | `integer` | 0/821 | 0.00% |
| `phone` | `string` | 0/821 | 0.00% |
| `sim_actor_id` | `string` | 0/821 | 0.00% |
| `sim_event_ids` | `array` | 0/821 | 0.00% |
| `supply_role` | `string` | 0/821 | 0.00% |

Three real sample rows/documents (compact view; arrays show their count and first actual element):

- `company-001`: `{"id":"vend-electricity","display_name":"Havenwood Municipal Utilities","payment_terms":"Due on receipt","payment_terms_days":0,"supply_role":"utility","joined_date":"2025-10-20"}`
- `company-001`: `{"id":"vend-government","display_name":"Copperfield Department of Revenue","payment_terms":"Due on receipt","payment_terms_days":0,"supply_role":"government","joined_date":"2026-01-05"}`
- `company-001`: `{"id":"vend-landlord","display_name":"Granite Bay Commercial Properties","payment_terms":"Due on receipt","payment_terms_days":0,"supply_role":"premises","joined_date":"2025-10-13"}`

## 5. Nested structures in the v4 schema

These are not additional top-level columns, but they are required to interpret the array/object columns above:

| Nested structure | Fields observed/defined | Used by |
|---|---|---|
| `Address` | `line1`, `line2`, `city`, `state`, `postal_code`, `country` | company, customer, vendor |
| `DocumentLine` | `line_num`, `item_id`, `item_name`, `description`, `quantity`, `unit_price_amount`, `amount` | invoice, sales receipt, bill item lines |
| `AccountLine` | `line_num`, `account_id`, `account_name`, `description`, `amount` | bill account lines |
| `PaymentApplication` | `document_id`, `amount` | customer and bill payments |
| `JournalLine` | `line_num`, `account_id`, `account_name`, `description`, `debit_amount`, `credit_amount`, `customer_id`, `vendor_id`, `document_id` | journal entries |
| `PayrollLine` | `employee_id`, `employee_name`, `gross_amount` | payroll runs |
| `ChangeOrder` | `sim_day`, `date`, `amount` | projects |
| `Reschedule` | no nested fields observed because all 203 project `reschedules` arrays are empty in this archive | projects |
| `StatusChange` | `sim_day`, `date`, `status` | projects |
| Aging row | `document_id`, `party`, `due_date`, `days_past_due`, `bucket`, `balance` | AP/AR aging |
| Report series | full-period/monthly or period-end/quarter-end financial objects | P&L and balance sheet |

Important schema conventions:

- IDs and names are company-scoped. Canonical keys must include `company_id`; `cust-customer-3` can refer to different parties in different companies.
- `doc_number` is advisory and must not be a primary key.
- Amounts are decimal strings, not floating-point values. Normalization should use `Decimal`.
- Bank-feed amounts are signed: debit increases checking; credit decreases it.
- The observation/status date is the final simulation day. Bill/invoice paid/open status must be derived from applications and the chosen as-of date.
- `sim_*` and `provenance_note` fields are generator provenance. They are valuable for traceability and label construction but can leak simulation ground truth; keep them out of provider inputs and benchmark features unless explicitly justified.

## 6. Required field coverage for LedgerGuard

| Requested concept | Status | Real source and caveat |
|---|---|---|
| company ID | **present** | `index.json.company_id` and directory name; inject into every normalized key because entity IDs are company-scoped. `manifest.dataset_id` is a separate content/world ID. |
| transaction ID | **present** | Each transaction-like record has `id`; bank feed also has `source_document_id`. There is no universal field literally named `transaction_id`. |
| bill ID | **present** | `bills.id`; payment links use `applications[].document_id`. |
| invoice ID | **present** | `invoices.id`; receipt links use `applications[].document_id`; estimates may have `invoice_id`. |
| vendor | **present** | Vendor master plus `vendor_id` / `vendor_name` on bills and bill payments. |
| customer | **present** | Customer master plus `customer_id` / `customer_name` on sales and receipt entities. |
| description | **present** | Account/item descriptions and line-level descriptions; not every top-level transaction has a separate description. |
| memo | **present** | Present on bills, invoices, sales receipts, payments, journal entries, and bank transactions. |
| amount | **present** | `amount`, `total_amount`, line amounts, report balances. All are decimal strings except `index.json.financials_cents`, which uses integer cents. |
| date | **present** | Transaction entities use `txn_date` or `date`; bills/invoices also have `due_date`; master data has relationship dates. |
| currency | **present** | `manifest.currency` and report currency; it is company-level, not repeated on each source record. |
| category | **present, entity-specific** | `bills.cost_category`, `journal_entries.purpose`, `bank_transactions.kind`, account types/subtypes, and project/estimate kinds. There is no single universal category field. |
| account | **present** | Chart of accounts plus posting/source/deposit/payment/income account IDs and line account IDs. |
| status | **partial / derived** | Explicit on projects and estimates. Bill/invoice payment status is not stored directly; derive it from payment applications and the observation date/aging reports. |
| payment destination | **missing** | `payment_account_id` is the company's source account, not the vendor's bank destination. Any destination/change signal must be a disclosed synthetic extension. |
| payment method | **missing** | No check/ACH/card method field for bill payments or customer payments. |
| reference number | **present** | `doc_number` exists but is advisory; reliable links use entity `id`, `source_document_id`, and `applications[].document_id`. |
| transaction type | **present / derived** | File/entity type is authoritative; bank feed adds `kind`, journals add `purpose`, and bills add `expense_kind`. |
| business type / industry | **present** | `company.industry_naics`, `company.industry_title`, plus `index.profile` and `index.archetype`. |

## 7. Recommended raw → canonical mapping

The canonical layer should preserve actual records rather than force all accounting entities into a transaction-shaped row. The following mapping is safe for Phase 1:

| Canonical field | Direct source | Rule / caveat |
|---|---|---|
| `record_id` | entity `id` | Make globally stable as `company_id:record_type:id`; never key on `doc_number`. |
| `company_id` | directory/index `company_id` | Required on every canonical record; not present inside most YAML rows. |
| `dataset_id` | `manifest.dataset_id` | Preserve as dataset-world provenance, separate from company ID. |
| `timestamp` | `txn_date` or `date` | Parse to a date/datetime. Master records should use their relevant relationship date or leave transaction timestamp unset. |
| `record_type` | logical filename/entity | Use a controlled enum: bill, bill_payment, invoice, customer_payment, sales_receipt, bank_transaction, journal_entry, etc. |
| `vendor_id`, `vendor_name` | bills/bill payments; vendor lookup | Direct for AP entities; null elsewhere. |
| `customer_id`, `customer_name` | invoices/receipts/payments; customer lookup | Direct for AR entities; null elsewhere. |
| `counterparty_id`, `counterparty_name` | vendor or customer fields | Derived alias based on record type; retain the typed vendor/customer fields too. |
| `description` | line description or account/item description | Do not overwrite `memo`; multiple line descriptions may require a list or deterministic concatenation. |
| `memo` | source `memo` | Direct where present, otherwise null. |
| `amount` | `total_amount` or `amount` | Convert with `Decimal`; preserve signed bank amounts. Journal entries should not invent a net amount (they balance to zero); keep lines and optionally derive total debits as a named feature. |
| `currency` | `manifest.currency` | Join by company/world. |
| `category` | cost category / journal purpose / bank kind | Keep the source-specific category and record which field supplied it. |
| `account_ids` | entity account fields and nested lines | Prefer a list/typed role map because one generic account loses debit/credit/source/deposit meaning. |
| `source_document_ids` | bank `source_document_id`; payment applications | Store as a list of typed references. Resolve each ID inside the same company. |
| `invoice_id`, `bill_id` | own record ID or resolved application/source link | Populate only after deterministic entity resolution, never by prefix alone if an exact company-scoped lookup is available. |
| `payment_id` | payment record `id` | Keep `sim_payment_id` only as provenance/label metadata, not as a production-facing identifier. |
| `status` | explicit status or derived payment state | Record `status_source` as `direct` or `derived_as_of`; do not pretend the source supplies bill/invoice status directly. |
| `source` | repository/archive/path/schema version | Example: `hf://CL251215/QuickBooks-Hackathon-2026@main/...`; include archive hash for reproducibility. |
| `raw_metadata` | untouched source row | Preserve nested lines and provenance so normalization is lossless. Restrict leakage-prone `sim_*` fields from inference views. |

### Entity-to-LedgerGuard use

| LedgerGuard need | Dataset entities | Feasibility |
|---|---|---|
| Vendor bill proposed actions | bills + vendors + accounts + AP aging | Strong: amount, due date, vendor, cost/account context, and outstanding balance are available. |
| Duplicate-obligation candidates | bills ↔ bill payments/applications; invoices ↔ customer payments/applications; bank source links; journal context | Strong for exact/document-linked candidates. Semantic near-duplicates must be injected as disclosed scenarios because the source books/feed are intentionally clean. |
| Vendor historical baseline | bills + bill payments + vendors | Strong for counts, amount statistics, timing, memo/cost/account history, and payment history. |
| Recent ledger history | bank transactions + journals + commercial documents | Strong, with deterministic date windows and company scoping. |
| Business context | company + index + manifest + accounts | Strong for industry/profile/currency/chart; no real user constraints. |
| `PAY_VENDOR_BILL` | bills + AP aging + bill payments | Directly supported for simulated proposed actions. |
| `POST_TRANSACTION` / `ADD_TRANSACTION` | bank transactions + journals + bills/invoices/sales receipts | Supported as runtime proposals derived from real records; execution remains simulated. |
| `MATCH_EXISTING` | document IDs, applications, bank source links, candidate similarity | Supported; exact matches are deterministic, semantic matching is a later provider judgment. |

## 8. Fields that must remain optional or synthetic

### Optional because real support is entity-dependent

- `vendor`, `customer`, `counterparty`, `project_id`, `description`, `memo`, `category`, `account_ids`, `invoice_id`, `bill_id`, `payment_id`, and `status` must be optional or typed by record kind.
- `currency` is required after the manifest join but absent on raw transaction rows.
- Direct bill/invoice status is unavailable; a derived as-of status must carry provenance.

### Disclosed synthetic extensions for LedgerGuard

- Proposed-agent fields: `action_id`, `action_type`, `agent_goal`, `agent_reasoning_summary`, and proposed execution timestamp.
- Payment-destination fields: `previous_destination`, `new_destination`, destination fingerprint/account metadata, and change timestamp. The source dataset has no vendor bank destination.
- User policy fields: user constraints, approval limits, allowlists, or explicit goal constraints.
- Scenario/evaluation fields: scenario ID/type, source record IDs, exact modifications, modification reason, expected action, expected risk flags, and label provenance.
- Missing-context/business-purpose perturbations when the real memo/description is intentionally removed or made ambiguous.

Synthetic extensions must never silently replace source values. Store them in a separate namespace/object and preserve `source_record_ids` plus the exact transformation.

## 9. Phase 0 conclusions

1. The official sponsor data is a 100-company, one-year, internally consistent synthetic accounting world in YAML RWM v4 format—not the guessed CSV layout.
2. The strongest LedgerGuard base is AP: bills, bill payments, vendors, accounts, bank links, and AP aging support realistic vendor-payment context and traceability.
3. Exact payment/document linkage is excellent; messy duplicates and unmatched bank-feed behavior are intentionally absent and therefore must be disclosed stress-test modifications.
4. Vendor payment destination and payment method are genuinely missing. A destination-change hero case must be a clearly labeled synthetic extension.
5. Company scope is mandatory for every key. Money should normalize to `Decimal`, and `doc_number` must never be used as identity.
6. Generator-only `sim_*` fields are useful for scenario lineage but risk label leakage. The Phase 1 model should preserve them in restricted raw metadata and exclude them from normal AccountingState/provider context.
7. Recommended next step, only after user confirmation: Phase 1 normalization and typed domain models built around the mappings above.

## 10. Reproducibility notes

- Local raw archive: `data/raw/hackathon-100-participant.tar.gz`
- Extracted raw tree: `data/raw/hackathon-100/`
- Phase 0 profiler: `tools/profile_quickbooks_dataset.rb`
- The profiler reads raw data only and does not normalize or mutate it.
