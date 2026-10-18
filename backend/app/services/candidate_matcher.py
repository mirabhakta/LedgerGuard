"""Transparent, dependency-free candidate retrieval."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal

from backend.app.models.accounting import CanonicalAccountingRecord
from backend.app.models.action import ProposedAction
from backend.app.models.state import CandidateMatch


class CandidateMatcher:
    def __init__(self, *, top_k: int = 5, window_days: int = 90) -> None:
        if top_k < 1 or window_days < 0:
            raise ValueError("top_k must be positive and window_days non-negative")
        self.top_k = top_k
        self.window_days = window_days

    def match(
        self,
        action: ProposedAction,
        records: tuple[CanonicalAccountingRecord, ...],
    ) -> tuple[CandidateMatch, ...]:
        as_of = action.timestamp.date()
        matches: list[CandidateMatch] = []
        for record in records:
            if record.company_id != action.company_id or record.timestamp is None:
                continue
            distance = (as_of - record.timestamp).days
            if distance < 0 or distance > self.window_days:
                continue
            score, reasons = self._score(action, record, distance)
            if not reasons:
                continue
            matches.append(
                CandidateMatch(
                    ledger_id=record.record_id,
                    source_id=record.source_id,
                    record_type=record.record_type.value,
                    date=record.timestamp,
                    amount=record.amount,
                    vendor=record.vendor_name or record.customer_name,
                    category=record.category,
                    description=record.description or record.memo,
                    status=record.status,
                    match_score=min(score, 1.0),
                    match_reasons=tuple(reasons),
                )
            )
        return tuple(
            sorted(
                matches,
                key=lambda item: (-item.match_score, -item.date.toordinal(), item.ledger_id),
            )[
                : self.top_k
            ]
        )

    @staticmethod
    def _score(
        action: ProposedAction, record: CanonicalAccountingRecord, distance: int
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        if action.source_document_id and (
            action.source_document_id == record.source_id
            or action.source_document_id in record.source_document_ids
        ):
            score += 0.55
            reasons.append("EXACT_DOCUMENT_LINK")
        action_party = action.vendor_id or action.counterparty_id
        if action_party and action_party in {record.vendor_id, record.customer_id, record.counterparty_id}:
            score += 0.20
            reasons.append("SAME_COUNTERPARTY")
        if record.amount is not None:
            difference = abs(record.amount - action.amount)
            tolerance = max(action.amount * Decimal("0.05"), Decimal("1"))
            if difference == 0:
                score += 0.15
                reasons.append("EXACT_AMOUNT")
            elif difference <= tolerance:
                score += 0.10
                reasons.append("NEAR_AMOUNT")
        if distance <= 7:
            score += 0.07
            reasons.append("NEARBY_DATE")
        if action.proposed_category and action.proposed_category == record.category:
            score += 0.03
            reasons.append("SAME_CATEGORY")
        action_text = _normalize_text(action.agent_goal)
        record_text = _normalize_text(" ".join(filter(None, (record.description, record.memo))))
        if action_text and record_text:
            overlap = len(set(action_text.split()) & set(record_text.split()))
            if overlap:
                score += min(0.05, overlap * 0.01)
                reasons.append("TEXT_TOKEN_OVERLAP")
        return score, reasons


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w]+", " ", normalized).strip()
