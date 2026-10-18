"""Hand-written heuristic baseline.

Reads only `AccountingState` (mostly `deterministic_features`, plus action text and user constraints), so it
sees exactly what the semantic providers see. Confidences are fixed per heuristic, not learned.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from backend.app.models.risk import RiskAssessment, RiskSignal
from backend.app.models.state import AccountingState

PAYMENT_ACTIONS = {"PAY_VENDOR_BILL"}


@dataclass(frozen=True)
class RulesConfig:
    dup_strong_amount_pct: float = 0.02
    dup_strong_days: int = 5
    dup_weak_amount_pct: float = 0.05
    dup_weak_days: int = 10
    dup_strong_score: float = 0.92
    dup_weak_score: float = 0.65
    dup_none_score: float = 0.05
    dup_confidence: float = 0.8

    destination_recent_days: int = 14
    destination_changed_score: float = 0.9
    unknown_payee_score: float = 0.6
    counterparty_none_score: float = 0.05
    counterparty_confidence: float = 0.8

    missing_base: float = 0.1
    missing_no_document: float = 0.35
    missing_unknown_payee: float = 0.3
    missing_vague_memo: float = 0.25
    vague_memo_max_len: int = 25
    missing_confidence: float = 0.7

    anomaly_z_start: float = 3.0
    anomaly_z_span: float = 6.0
    anomaly_ratio_flag: float = 2.0
    anomaly_flag_score: float = 0.85
    anomaly_confidence: float = 0.7

    goal_violation_score: float = 0.95
    goal_ok_score: float = 0.05
    goal_confidence_parsed: float = 0.9
    goal_confidence_default: float = 0.7

    personal_keywords: tuple[str, ...] = (
        "spa", "netflix", "grocery", "whole foods", "vacation", "nordstrom", "peloton", "golf", "country club",
    )
    transfer_keywords: tuple[str, ...] = ("transfer to", "xfer", "to sav", "savings")
    vague_memo_words: tuple[str, ...] = ("services rendered", "consulting", "retainer", "support", "invoice attached")
    role_keywords: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "utility": ("utility", "utilities", "electric", "water", "gas"),
            "premises": ("rent", "landlord", "premises"),
            "insurance": ("insurance", "insurer"),
        }
    )


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


class RulesProvider:
    name = "rules"

    def __init__(self, config: RulesConfig | None = None):
        self.config = config or RulesConfig()

    async def evaluate(self, state: AccountingState) -> RiskAssessment:
        started = time.perf_counter()
        signals = {
            "goal_misalignment_risk": self._goal(state),
            "duplicate_obligation_risk": self._duplicate(state),
            "counterparty_change_risk": self._counterparty(state),
            "missing_context_risk": self._missing(state),
            "action_anomaly_risk": self._anomaly(state),
        }
        return RiskAssessment(
            **signals,
            model_name="rules-v1",
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _duplicate(self, state: AccountingState) -> RiskSignal:
        c, f = self.config, state.deterministic_features
        if not f.get("candidate_count"):
            return RiskSignal(value=c.dup_none_score, confidence=c.dup_confidence)
        same_party = f.get("closest_candidate_same_counterparty") or not f.get("vendor_known")
        delta = f.get("closest_candidate_amount_delta_pct", 1.0)
        days = f.get("closest_candidate_days_apart", 999)
        if same_party and delta <= c.dup_strong_amount_pct and days <= c.dup_strong_days:
            value = c.dup_strong_score
        elif same_party and delta <= c.dup_weak_amount_pct and days <= c.dup_weak_days:
            value = c.dup_weak_score
        else:
            value = c.dup_none_score
        return RiskSignal(value=value, confidence=c.dup_confidence)

    def _counterparty(self, state: AccountingState) -> RiskSignal:
        c, f = self.config, state.deterministic_features
        recent = f.get("destination_first_seen_days_ago")
        if f.get("payment_destination_changed") and (recent is None or recent <= c.destination_recent_days):
            value = c.destination_changed_score
        elif state.proposed_action.action_type in PAYMENT_ACTIONS and not f.get("vendor_known"):
            value = c.unknown_payee_score
        else:
            value = c.counterparty_none_score
        return RiskSignal(value=value, confidence=c.counterparty_confidence)

    def _missing(self, state: AccountingState) -> RiskSignal:
        c, f, action = self.config, state.deterministic_features, state.proposed_action
        value = c.missing_base
        is_payment = action.action_type in PAYMENT_ACTIONS
        if is_payment and not f.get("has_source_document"):
            value += c.missing_no_document
        if is_payment and not f.get("vendor_known"):
            value += c.missing_unknown_payee
        memo = str(action.metadata.get("memo") or "").lower()
        if is_payment and (len(memo) < c.vague_memo_max_len or any(w in memo for w in c.vague_memo_words)):
            value += c.missing_vague_memo
        return RiskSignal(value=_clip(value), confidence=c.missing_confidence)

    def _anomaly(self, state: AccountingState) -> RiskSignal:
        c, f, action = self.config, state.deterministic_features, state.proposed_action
        text = " ".join(filter(None, [action.counterparty, action.vendor, str(action.metadata.get("bank_descriptor") or "")])).lower()
        if any(k in text for k in c.personal_keywords) or any(k in text for k in c.transfer_keywords):
            return RiskSignal(value=c.anomaly_flag_score, confidence=c.anomaly_confidence)
        ratio = f.get("amount_ratio_to_vendor_median") or f.get("amount_ratio_to_company_bill_median")
        z = abs(f.get("amount_robust_z") or 0.0)
        value = _clip((z - c.anomaly_z_start) / c.anomaly_z_span)
        if ratio is not None and ratio >= c.anomaly_ratio_flag and f.get("vendor_known"):
            value = max(value, c.anomaly_flag_score)
        return RiskSignal(value=value, confidence=c.anomaly_confidence)

    def _goal(self, state: AccountingState) -> RiskSignal:
        c, action = self.config, state.proposed_action
        rules = [str(r) for r in state.business_context.user_constraints.get("rules", [])]
        if not rules:
            return RiskSignal(value=c.goal_ok_score, confidence=c.goal_confidence_default)
        payee = (action.vendor or action.counterparty or "").lower()
        role = str(state.deterministic_features.get("vendor_supply_role") or "").lower()
        category = (action.proposed_category or "").lower()
        for rule in rules:
            text = rule.lower()
            hold = re.search(r"do not pay (?:anything to )?(.+?)(?: until| before|\.|$)", text)
            if hold and payee and hold.group(1).strip() in payee:
                return RiskSignal(value=c.goal_violation_score, confidence=c.goal_confidence_parsed)
            only = re.search(r"only pay (\w+)", text)
            if only:
                keywords = next((kw for kw in c.role_keywords.values() if only.group(1) in kw), (only.group(1),))
                haystack = f"{role} {category} {payee}"
                if not any(k in haystack for k in keywords):
                    return RiskSignal(value=c.goal_violation_score, confidence=c.goal_confidence_parsed)
                return RiskSignal(value=c.goal_ok_score, confidence=c.goal_confidence_parsed)
        return RiskSignal(value=c.goal_ok_score, confidence=c.goal_confidence_default)
