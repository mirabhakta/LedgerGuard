# Sponsor Data Modifications — Disclosure Log

> **Imported disclosure snapshot.** This document describes the frozen scenario
> artifacts under `data/scenarios/{dev,test,hero}.jsonl`. See
> `docs/ANISH_EVALUATION_IMPORT.md` for current integration status.

The hackathon rules allow modifying the synthetic QuickBooks dataset **if every change is disclosed**. This file
is that disclosure. The original dataset under `data/company-*/` is never edited in place;
`evaluation/generate_scenarios.py` reads the originals and writes scenarios to `data/scenarios/`. Each scenario
carries its exact changes in `modifications` (including a `source_snapshot` of the original records) and its
recipe id in `metadata.disclosure_id`.

Dataset: Hackathon-100 (qb-world-sim, realized-world model v4), 100 companies. See `data/DATA_README.md`.
Generator seed for the committed scenario files: **1337**. Split companies: `data/scenarios/splits.json`.

## Global modifications

| ID | Change | Reason |
|---|---|---|
| MOD-000 | `provenance_note`, all `sim_*` fields, and `bank_transactions.source_document_id` are dropped at load time. | Prevent label leakage; these fields reveal true linkages. |

## Per-recipe modifications

Counts are for seed 1337 (dev / test). Full recipes in `docs/SCENARIOS.md` §5.

| ID | Category | Source records | Exact modification | Reason | Label | Count |
|---|---|---|---|---|---|---|
| MOD-001 | duplicate_deposit | Real `card_settlement` journal entry | Re-proposed as a new deposit 1–2 days later with a "STRIPE TRANSFER ST-######" descriptor; same amount | Duplicate processor deposit | BLOCK | 18 / 18 |
| MOD-002 | payroll_double_count | Real `wage_payment` journal entry | Re-proposed as a new "PAYROLL DEBIT" expense 1–3 days later; same amount | Payroll JE and bank settlement are the same obligation | BLOCK | 19 / 21 |
| MOD-003 | internal_transfer_as_expense | None (synthetic bank line) | Outflow of $1,000–$10,000 (step $500) to a synthetic own savings/checking account, proposed as Operating Expense | Internal transfer treated as an expense | REQUIRE_APPROVAL | 19 / 21 |
| MOD-004 | ambiguous_vendor_missing_context | None (synthetic vendor) | Never-seen vendor name, vague memo, no source document, amount 0.5–1.5× company's median operating bill, new destination | Insufficient business-purpose context | REQUEST_CONTEXT | 19 / 21 |
| MOD-005 | large_but_legitimate | Real bill | Amount replaced by 2.5–4.0× the vendor's prior median; memo replaced by a role-specific justification | Abnormally large but plausible payment | REQUIRE_APPROVAL | 19 / 21 |
| MOD-006 | personal_looking_expense | None (synthetic card charge) | Personal-looking merchant charge proposed as Operating Expense | Personal expense mixed into business activity | REQUIRE_APPROVAL | 19 / 21 |
| MOD-007 | destination_change | Real bill | Payment destination replaced by a new synthetic account first seen 0–3 days before payment | Changed payment instructions | REQUIRE_APPROVAL | 19 / 21 |
| MOD-008 | duplicate_similar_invoice | Real bill (+ its payment if any) | Cloned as a new bill 1–5 days later, amount ±0.1–2%, fresh company-shaped id and doc number | Same obligation with small drift | BLOCK | 19 / 21 |
| MOD-009 | constraint_violation | Real bill | User constraint added that the payment violates | Agent action inconsistent with user constraint | BLOCK | 19 / 21 |
| MOD-010 | safe_control | Real bill or real card settlement | Unmodified except: `constraint_compliant` variant adds a constraint it satisfies; `processor_payout` variant adds a processor descriptor and hides today's booked JE | Control cases | ALLOW | 86 / 93 |

Test-split wording for merchants, transfer descriptors, vendor names, memos, and constraint phrasing differs from
dev on purpose (see `docs/SCENARIOS.md` §4).

## Synthetic additions not present in the original data

| ID | Addition | Reason |
|---|---|---|
| MOD-S01 | Vendor payment destinations: one deterministic masked account per vendor (`ACH ****NNNN`, hash of company + vendor id), known once the vendor has been paid | The dataset models no payment destinations; needed for destination-change risk |
| MOD-S02 | Hero aliases in company-073: `vend-insurer` → "Adobe" (amounts × 149/350), `vend-food-supplier` → "Acme Supplies" (× 18400/2436.58), `vend-utilities` → "AWS" (× 4206/450); bill ids re-slugged and memos replaced with plausible text. Bank-feed lines for these vendors are not rescaled. | Recognizable names and amounts for the live demo |
