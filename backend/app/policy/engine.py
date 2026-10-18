from __future__ import annotations

from backend.app.models.action import FinalAction
from backend.app.models.policy import PolicyDecision, PrecheckResult
from backend.app.models.risk import RiskAssessment
from backend.app.models.state import AccountingState
from backend.app.policy.config import PolicyConfig


class PolicyEngine:
    def decide(
        self,
        state: AccountingState,
        assessment: RiskAssessment,
        precheck_result: PrecheckResult,
        config: PolicyConfig,
    ) -> PolicyDecision:
        provider = assessment.model_name

        if assessment.had_error:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["PROVIDER_ERROR"],
                triggered_thresholds=[],
                provider=provider,
                fail_safe_triggered=True,
            )

        if precheck_result.hard_block:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=precheck_result.reason_codes,
                triggered_thresholds=[],
                provider=provider,
            )

        if precheck_result.requires_review:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=precheck_result.reason_codes,
                triggered_thresholds=[],
                provider=provider,
            )

        all_signals = [
            assessment.goal_misalignment_risk,
            assessment.duplicate_obligation_risk,
            assessment.counterparty_change_risk,
            assessment.missing_context_risk,
            assessment.action_anomaly_risk,
        ]

        min_confidence = min(signal.confidence for signal in all_signals)

        if min_confidence < config.minimum_confidence_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["LOW_PROVIDER_CONFIDENCE"],
                triggered_thresholds=["minimum_confidence_threshold"],
                provider=provider,
            )

        if assessment.goal_misalignment_risk.value >= config.goal_misalignment_block_threshold:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=["GOAL_MISALIGNMENT"],
                triggered_thresholds=["goal_misalignment_block_threshold"],
                provider=provider,
            )

        if assessment.duplicate_obligation_risk.value >= config.duplicate_block_threshold:
            return PolicyDecision(
                final_action=FinalAction.BLOCK,
                reason_codes=["DUPLICATE_OBLIGATION"],
                triggered_thresholds=["duplicate_block_threshold"],
                provider=provider,
            )

        if assessment.counterparty_change_risk.value >= config.counterparty_review_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["COUNTERPARTY_CHANGE_RISK"],
                triggered_thresholds=["counterparty_review_threshold"],
                provider=provider,
            )

        if assessment.missing_context_risk.value >= config.missing_context_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUEST_CONTEXT,
                reason_codes=["MISSING_CONTEXT"],
                triggered_thresholds=["missing_context_threshold"],
                provider=provider,
            )

        if assessment.action_anomaly_risk.value >= config.anomaly_review_threshold:
            return PolicyDecision(
                final_action=FinalAction.REQUIRE_APPROVAL,
                reason_codes=["ACTION_ANOMALY"],
                triggered_thresholds=["anomaly_review_threshold"],
                provider=provider,
            )

        return PolicyDecision(
            final_action=FinalAction.ALLOW,
            reason_codes=["LOW_RISK"],
            triggered_thresholds=[],
            provider=provider,
        )
