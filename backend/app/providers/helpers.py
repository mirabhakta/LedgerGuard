from backend.app.models.risk import RiskAssessment, RiskSignal


def provider_error_assessment(
    *,
    model_name: str,
    latency_ms: float,
    error_code: str,
    error_message: str,
) -> RiskAssessment:
    unknown = RiskSignal(
        value=0.5,
        confidence=0.0,
    )

    return RiskAssessment(
        goal_misalignment_risk=unknown,
        duplicate_obligation_risk=unknown,
        counterparty_change_risk=unknown,
        missing_context_risk=unknown,
        action_anomaly_risk=unknown,
        model_name=model_name,
        latency_ms=latency_ms,
        had_error=True,
        used_fallback=True,
        error_code=error_code,
        error_message=error_message,
    )
