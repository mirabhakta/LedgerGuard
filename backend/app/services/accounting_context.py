"""Assemble the provider-neutral context blocks that `build_accounting_state` reads from
`Scenario.original_data`: `business_context`, `candidate_matches`, `recent_ledger_history`,
and `deterministic_features`.

Everything here is deterministic code over the books (dates, amounts, exact facts). No semantic judgment.
History is strictly before `as_of`, so nothing from the future of the proposed action is visible.
"""

from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.app.models.action import ProposedAction
from backend.app.services.sponsor_data import CompanyBooks

CANDIDATE_LOOKBACK_DAYS = 45
CANDIDATE_AMOUNT_TOLERANCE = 0.05
CANDIDATE_WINDOW_DAYS = 7
MAX_CANDIDATES = 6
MAX_VENDOR_HISTORY_ROWS = 6
MAX_BANK_HISTORY_ROWS = 8
MAX_PATTERNS = 8


@dataclass(frozen=True)
class ContextRequest:
    books: CompanyBooks
    action: ProposedAction
    as_of: date
    vendor_id: str | None = None
    user_constraints: dict[str, Any] | None = None
    exclude_record_ids: frozenset[str] = frozenset()


def default_destination(company_id: str, vendor_id: str) -> str:
    """Synthetic, deterministic payment destination per vendor (docs/MODIFICATIONS.md, MOD-S01)."""
    digest = hashlib.sha256(f"{company_id}:{vendor_id}".encode()).hexdigest()
    return f"ACH ****{int(digest[:8], 16) % 10000:04d}"


def _d(value: str) -> date:
    return date.fromisoformat(value)


def _bill_category(bill: dict[str, Any]) -> str:
    if bill["account_lines"]:
        return bill["account_lines"][0]["account_name"]
    return "Inventory Asset"


def _bill_status(books: CompanyBooks, bill_id: str, as_of: date) -> str:
    paid = any(
        app["document_id"] == bill_id and _d(p["txn_date"]) < as_of
        for p in books.bill_payments
        for app in p["applications"]
    )
    return "paid" if paid else "open"


def _amount_stats(amounts: list[float]) -> dict[str, float]:
    if not amounts:
        return {}
    ordered = sorted(amounts)
    median = statistics.median(ordered)
    mad = statistics.median(abs(a - median) for a in ordered)

    def pct(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))]

    return {
        "count": float(len(ordered)),
        "median": round(median, 2),
        "mean": round(statistics.fmean(ordered), 2),
        "p10": round(pct(0.10), 2),
        "p90": round(pct(0.90), 2),
        "min": round(ordered[0], 2),
        "max": round(ordered[-1], 2),
        "mad": round(mad, 2),
    }


def _median_gap_days(dates: list[date]) -> float | None:
    ordered = sorted(dates)
    gaps = [(b - a).days for a, b in zip(ordered, ordered[1:])]
    return float(statistics.median(gaps)) if gaps else None


def _vendor_bills(req: ContextRequest, vendor_id: str) -> list[dict[str, Any]]:
    return [
        b
        for b in req.books.bills
        if b["vendor_id"] == vendor_id and _d(b["txn_date"]) < req.as_of and b["id"] not in req.exclude_record_ids
    ]


def _vendor_payments(req: ContextRequest, vendor_id: str) -> list[dict[str, Any]]:
    return [p for p in req.books.bill_payments if p["vendor_id"] == vendor_id and _d(p["txn_date"]) < req.as_of]


def _patterns(req: ContextRequest) -> list[str]:
    patterns: list[str] = []
    for vendor in req.books.vendors:
        bills = _vendor_bills(req, vendor["id"])
        if len(bills) < 3:
            continue
        amounts = [float(b["total_amount"]) for b in bills]
        gap = _median_gap_days([_d(b["txn_date"]) for b in bills])
        patterns.append(
            f"{vendor['display_name']} ({vendor['supply_role']}) bills about every {gap:.0f} days; "
            f"median ${statistics.median(amounts):,.2f}; {len(bills)} bills on file."
        )
    purposes = {j["purpose"] for j in req.books.journal_entries if _d(j["txn_date"]) < req.as_of}
    if "wage_payment" in purposes:
        patterns.append("Payroll is paid from checking and booked as wage_payment journal entries ('Wages paid' on the bank feed).")
    if "card_settlement" in purposes:
        patterns.append("Card takings are settled by the processor into checking and booked as card_settlement journal entries.")
    if {"financing_draw", "financing_repayment"} & purposes:
        patterns.append("The business draws on and repays a line of credit through checking.")
    return patterns[:MAX_PATTERNS]


def _journal_amount(entry: dict[str, Any]) -> float:
    return float(sum(float(line["debit_amount"]) for line in entry["lines"]))


def _vendor_candidates(req: ContextRequest, vendor_id: str) -> list[dict[str, Any]]:
    lookback = req.as_of.toordinal() - CANDIDATE_LOOKBACK_DAYS
    bills = [b for b in _vendor_bills(req, vendor_id) if _d(b["txn_date"]).toordinal() >= lookback]
    amount = req.action.amount or 0.0
    bills.sort(key=lambda b: (abs(float(b["total_amount"]) - amount), -_d(b["txn_date"]).toordinal()))
    bills = sorted(bills[:MAX_CANDIDATES], key=lambda b: b["txn_date"], reverse=True)
    return [
        {
            "record_id": b["id"],
            "date": b["txn_date"],
            "amount": float(b["total_amount"]),
            "vendor": b["vendor_name"],
            "category": _bill_category(b),
            "description": b["memo"],
            "status": _bill_status(req.books, b["id"], req.as_of),
            "metadata": {"record_type": "bill", "doc_number": b["doc_number"], "due_date": b["due_date"]},
        }
        for b in bills
    ]


def _ledger_candidates(req: ContextRequest, purposes: set[str]) -> list[dict[str, Any]]:
    """Booked journal entries near the action's bank date with a similar amount."""
    action = req.action
    if action.amount is None:
        return []
    bank_date = _d(action.metadata.get("bank_date", req.as_of.isoformat()))
    matches = []
    for entry in req.books.journal_entries:
        if entry["purpose"] not in purposes or entry["id"] in req.exclude_record_ids:
            continue
        entry_date = _d(entry["txn_date"])
        if entry_date >= req.as_of or abs((entry_date - bank_date).days) > CANDIDATE_WINDOW_DAYS:
            continue
        amount = _journal_amount(entry)
        if abs(amount - action.amount) > CANDIDATE_AMOUNT_TOLERANCE * action.amount:
            continue
        matches.append(
            {
                "record_id": entry["id"],
                "date": entry["txn_date"],
                "amount": round(amount, 2),
                "vendor": None,
                "category": entry["lines"][0]["account_name"],
                "description": entry["memo"],
                "status": "posted",
                "metadata": {"record_type": "journal_entry", "purpose": entry["purpose"]},
            }
        )
    matches.sort(key=lambda m: (abs(m["amount"] - action.amount), abs((_d(m["date"]) - bank_date).days)))
    return matches[:MAX_CANDIDATES]


LEDGER_PURPOSES_BY_ACTION = {
    "RECORD_DEPOSIT": {"card_settlement", "deposit_receipt", "financing_draw"},
    "RECORD_EXPENSE": {"wage_payment", "financing_repayment", "owner_distribution"},
}


def _recent_history(req: ContextRequest, vendor_id: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if vendor_id:
        for b in sorted(_vendor_bills(req, vendor_id), key=lambda b: b["txn_date"], reverse=True)[:MAX_VENDOR_HISTORY_ROWS]:
            rows.append(
                {
                    "date": b["txn_date"],
                    "type": "bill",
                    "record_id": b["id"],
                    "counterparty": b["vendor_name"],
                    "amount": float(b["total_amount"]),
                    "status": _bill_status(req.books, b["id"], req.as_of),
                }
            )
        for p in sorted(_vendor_payments(req, vendor_id), key=lambda p: p["txn_date"], reverse=True)[:MAX_VENDOR_HISTORY_ROWS]:
            rows.append(
                {
                    "date": p["txn_date"],
                    "type": "bill_payment",
                    "record_id": p["id"],
                    "counterparty": p["vendor_name"],
                    "amount": float(p["amount"]),
                    "applied_to": [a["document_id"] for a in p["applications"]],
                }
            )
    bank = [t for t in req.books.bank_transactions if _d(t["date"]) < req.as_of]
    for t in bank[-MAX_BANK_HISTORY_ROWS:]:
        rows.append({"date": t["date"], "type": "bank_feed", "record_id": t["id"], "amount": float(t["amount"]), "memo": t["memo"], "kind": t["kind"]})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def _features(
    req: ContextRequest,
    vendor: dict[str, Any] | None,
    stats: dict[str, float],
    known_destinations: list[str],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    action = req.action
    amount = action.amount or 0.0
    features: dict[str, Any] = {
        "action_type": action.action_type,
        "amount": amount,
        "has_source_document": bool(action.source_document_id),
        "vendor_known": vendor is not None,
    }

    if vendor is not None:
        bills = _vendor_bills(req, vendor["id"])
        payments = _vendor_payments(req, vendor["id"])
        bill_dates = [_d(b["txn_date"]) for b in bills]
        features.update(
            {
                "vendor_supply_role": vendor["supply_role"],
                "vendor_prior_bill_count": len(bills),
                "vendor_prior_payment_count": len(payments),
                "days_since_vendor_first_seen": (req.as_of - _d(vendor["joined_date"])).days,
                "days_since_last_vendor_bill": (req.as_of - max(bill_dates)).days if bill_dates else None,
                "vendor_typical_cadence_days": _median_gap_days(bill_dates),
            }
        )
    if stats:
        median = stats["median"]
        scale = max(stats["mad"] * 1.4826, 0.01 * median, 0.01)
        features.update(
            {
                "vendor_amount_median": median,
                "amount_ratio_to_vendor_median": round(amount / median, 4) if median else None,
                "amount_robust_z": round((amount - median) / scale, 3),
                "amount_within_vendor_p10_p90": stats["p10"] <= amount <= stats["p90"],
            }
        )
    else:
        operating = [float(b["total_amount"]) for b in req.books.bills if _d(b["txn_date"]) < req.as_of]
        if operating:
            company_median = statistics.median(operating)
            features["company_bill_median"] = round(company_median, 2)
            features["amount_ratio_to_company_bill_median"] = round(amount / company_median, 4) if company_median else None

    destination = action.destination_account
    if destination is not None:
        features["payment_destination_known"] = destination in known_destinations
        features["payment_destination_changed"] = bool(known_destinations) and destination not in known_destinations
        first_seen = action.metadata.get("destination_first_seen")
        features["destination_first_seen_days_ago"] = (req.as_of - _d(first_seen)).days if first_seen else None

    features["candidate_count"] = len(candidates)
    if candidates and amount:
        reference = _d(action.metadata.get("bill_date") or action.metadata.get("bank_date") or req.as_of.isoformat())

        def delta(c: dict[str, Any]) -> float:
            return abs(c["amount"] - amount) / amount

        def days(c: dict[str, Any]) -> int:
            return abs((_d(c["date"]) - reference).days)

        similar = [c for c in candidates if delta(c) <= CANDIDATE_AMOUNT_TOLERANCE]
        closest = min(similar, key=lambda c: (days(c), delta(c))) if similar else min(candidates, key=lambda c: (delta(c), days(c)))
        features["candidates_within_amount_tolerance"] = len(similar)
        features.update(
            {
                "closest_candidate_id": closest["record_id"],
                "closest_candidate_amount_delta_pct": round(abs(closest["amount"] - amount) / amount, 5),
                "closest_candidate_days_apart": abs((_d(closest["date"]) - reference).days),
                "closest_candidate_status": closest["status"],
                "closest_candidate_same_counterparty": bool(vendor) and closest["vendor"] == vendor["display_name"],
            }
        )
    return features


def assemble_original_data(req: ContextRequest) -> dict[str, Any]:
    books = req.books
    vendor = books.vendor(req.vendor_id) if req.vendor_id else None

    vendor_history: dict[str, Any] = {}
    stats: dict[str, float] = {}
    known_destinations: list[str] = []
    if vendor is not None:
        bills = _vendor_bills(req, vendor["id"])
        payments = _vendor_payments(req, vendor["id"])
        stats = _amount_stats([float(b["total_amount"]) for b in bills])
        last_payment = max(payments, key=lambda p: p["txn_date"]) if payments else None
        vendor_history = {
            "vendor_id": vendor["id"],
            "display_name": vendor["display_name"],
            "supply_role": vendor["supply_role"],
            "payment_terms": vendor["payment_terms"],
            "first_seen": vendor["joined_date"],
            "bill_count": len(bills),
            "payment_count": len(payments),
            "last_payment_date": last_payment["txn_date"] if last_payment else None,
            "last_payment_amount": float(last_payment["amount"]) if last_payment else None,
            "typical_cadence_days": _median_gap_days([_d(b["txn_date"]) for b in bills]),
            "categories": sorted({_bill_category(b) for b in bills}),
        }
        if payments:
            known_destinations = [default_destination(books.company_id, vendor["id"])]
        candidates = _vendor_candidates(req, vendor["id"])
    else:
        candidates = _ledger_candidates(req, LEDGER_PURPOSES_BY_ACTION.get(req.action.action_type, set()))

    business_context = {
        "company_id": books.company_id,
        "business_type": f"{books.industry_title} ({books.profile})",
        "current_account": "Business Checking",
        "vendor_history": vendor_history,
        "historical_amount_stats": stats,
        "known_payment_destinations": known_destinations,
        "known_accounting_patterns": _patterns(req),
        "user_constraints": req.user_constraints or {},
        "metadata": {"as_of_date": req.as_of.isoformat(), "company_name": books.display_name},
    }

    return {
        "business_context": business_context,
        "candidate_matches": candidates,
        "recent_ledger_history": _recent_history(req, vendor["id"] if vendor else None),
        "deterministic_features": _features(req, vendor, stats, known_destinations, candidates),
    }
