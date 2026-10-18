"""Read-only loader for the sponsor Hackathon-100 dataset.

Fields that reveal simulation ground truth (`provenance_note`, every `sim_*` field, and the bank feed's
`source_document_id`) are dropped at load time so they can never reach a decision provider.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

LEAKY_KEYS = frozenset({"provenance_note", "source_document_id"})

CENT = Decimal("0.01")


def data_root() -> Path:
    return Path(os.environ.get("LEDGERGUARD_DATA_DIR", REPO_ROOT / "data"))


def money(value: str | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def strip_leaky_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: strip_leaky_fields(v)
            for k, v in value.items()
            if k not in LEAKY_KEYS and not k.startswith("sim_")
        }
    if isinstance(value, list):
        return [strip_leaky_fields(v) for v in value]
    return value


@dataclass(frozen=True)
class CompanyBooks:
    company_id: str
    dataset_id: str
    display_name: str
    profile: str
    industry_title: str
    accounts: list[dict[str, Any]]
    vendors: list[dict[str, Any]]
    bills: list[dict[str, Any]]
    bill_payments: list[dict[str, Any]]
    bank_transactions: list[dict[str, Any]]
    journal_entries: list[dict[str, Any]]
    vendor_aliases: dict[str, dict[str, Any]] = field(default_factory=dict)

    def vendor(self, vendor_id: str) -> dict[str, Any] | None:
        return next((v for v in self.vendors if v["id"] == vendor_id), None)

    def account_name(self, predicate) -> str | None:
        return next((a["name"] for a in self.accounts if predicate(a)), None)

    def with_vendor_alias(
        self,
        vendor_id: str,
        *,
        display_name: str,
        supply_role: str,
        amount_scale: Decimal,
        memo_template: str | None = None,
    ) -> CompanyBooks:
        """Return a copy where one vendor is renamed, its bill/payment amounts are scaled, its bill ids are
        re-slugged to the alias, and (optionally) its bill memos are replaced. `memo_template` may use
        `{period}`, the month before the bill date.

        Used only for disclosed hero-demo aliases (docs/MODIFICATIONS.md, MOD-S02).
        """
        slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")

        def scale(amount: str) -> str:
            return str(money(Decimal(amount) * amount_scale))

        def rename(bill_id: str) -> str:
            return re.sub(r"^bill-(?:[a-z-]+-)?(\d+)$", rf"bill-{slug}-\1", bill_id)

        def memo_for(bill: dict[str, Any]) -> str:
            if memo_template is None:
                return bill["memo"]
            period = (date.fromisoformat(bill["txn_date"]).replace(day=1) - timedelta(days=1)).strftime("%B %Y")
            return memo_template.format(period=period)

        vendor_bill_ids = {b["id"] for b in self.bills if b["vendor_id"] == vendor_id}

        vendors = [
            {**v, "display_name": display_name, "company_name": display_name, "supply_role": supply_role}
            if v["id"] == vendor_id
            else v
            for v in self.vendors
        ]
        bills = []
        for b in self.bills:
            if b["vendor_id"] != vendor_id:
                bills.append(b)
                continue
            bills.append(
                {
                    **b,
                    "id": rename(b["id"]),
                    "memo": memo_for(b),
                    "vendor_name": display_name,
                    "total_amount": scale(b["total_amount"]),
                    "item_lines": [{**ln, "amount": scale(ln["amount"])} for ln in b["item_lines"]],
                    "account_lines": [{**ln, "amount": scale(ln["amount"])} for ln in b["account_lines"]],
                }
            )
        payments = []
        for p in self.bill_payments:
            if p["vendor_id"] != vendor_id:
                payments.append(p)
                continue
            payments.append(
                {
                    **p,
                    "vendor_name": display_name,
                    "amount": scale(p["amount"]),
                    "applications": [
                        {
                            **a,
                            "document_id": rename(a["document_id"]) if a["document_id"] in vendor_bill_ids else a["document_id"],
                            "amount": scale(a["amount"]),
                        }
                        for a in p["applications"]
                    ],
                }
            )
        aliases = {
            **self.vendor_aliases,
            vendor_id: {
                "display_name": display_name,
                "supply_role": supply_role,
                "amount_scale": str(amount_scale),
                "memo_template": memo_template,
            },
        }
        return replace(self, vendors=vendors, bills=bills, bill_payments=payments, vendor_aliases=aliases)


@lru_cache(maxsize=1)
def load_index() -> list[dict[str, Any]]:
    with open(data_root() / "index.json") as f:
        return json.load(f)


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    with open(path) as f:
        loaded = yaml.load(f, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    return strip_leaky_fields(loaded or [])


@lru_cache(maxsize=8)
def load_company(company_id: str) -> CompanyBooks:
    entry = next((c for c in load_index() if c["company_id"] == company_id), None)
    if entry is None:
        raise KeyError(f"Unknown company_id: {company_id}")
    world = data_root() / company_id / "rwm-v4" / entry["dataset_id"]
    return CompanyBooks(
        company_id=company_id,
        dataset_id=entry["dataset_id"],
        display_name=entry["display_name"],
        profile=entry["profile"],
        industry_title=entry["industry_title"],
        accounts=_load_yaml(world / "accounts.yaml"),
        vendors=_load_yaml(world / "vendors.yaml"),
        bills=_load_yaml(world / "bills.yaml"),
        bill_payments=_load_yaml(world / "bill_payments.yaml"),
        bank_transactions=_load_yaml(world / "bank_transactions.yaml"),
        journal_entries=_load_yaml(world / "journal_entries.yaml"),
    )
