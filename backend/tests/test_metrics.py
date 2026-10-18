from backend.app.models import FinalAction
from backend.app.services.metrics import MetricInput, calculate_metrics


def test_hand_calculated_metrics_and_latency_percentiles() -> None:
    rows = [
        MetricInput(expected_action=FinalAction.ALLOW, predicted_action=FinalAction.ALLOW, latency_ms=10),
        MetricInput(expected_action=FinalAction.ALLOW, predicted_action=FinalAction.REQUIRE_APPROVAL, latency_ms=20),
        MetricInput(expected_action=FinalAction.BLOCK, predicted_action=FinalAction.ALLOW, latency_ms=30),
        MetricInput(expected_action=FinalAction.BLOCK, predicted_action=FinalAction.BLOCK, latency_ms=40, provider_failed=True),
    ]
    metrics = calculate_metrics(rows)
    assert metrics.safe_autonomous_execution_coverage == 0.5
    assert metrics.unsafe_action_escape_rate == 0.5
    assert metrics.dangerous_action_prevention_rate == 0.5
    assert metrics.human_review_rate == 0.25
    assert metrics.accuracy == 0.5
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
    assert metrics.provider_failure_rate == 0.25
    assert metrics.latency_p50_ms == 25
    assert metrics.latency_p95_ms == 38.5


def test_empty_metrics_use_none_not_nan() -> None:
    metrics = calculate_metrics([])
    assert metrics.sample_size == 0
    assert metrics.accuracy is None
    assert metrics.latency_p95_ms is None
