import pytest

from backend.app.services.metrics import decision_metrics, latency_metrics, percentile, wilson_interval


def row(expected, final, category="c", acceptable=None):
    return {
        "expected_action": expected,
        "final_action": final,
        "acceptable_actions": acceptable or [expected],
        "is_unsafe": expected != "ALLOW",
        "category": category,
    }


ROWS = [
    row("ALLOW", "ALLOW"),
    row("ALLOW", "ALLOW"),
    row("ALLOW", "REQUIRE_APPROVAL"),
    row("ALLOW", "BLOCK"),
    row("BLOCK", "BLOCK", acceptable=["BLOCK", "REQUIRE_APPROVAL"]),
    row("BLOCK", "REQUIRE_APPROVAL", acceptable=["BLOCK", "REQUIRE_APPROVAL"]),
    row("BLOCK", "ALLOW", acceptable=["BLOCK", "REQUIRE_APPROVAL"]),
    row("REQUEST_CONTEXT", "REQUEST_CONTEXT"),
]


def test_safety_and_workload_rates():
    m = decision_metrics(ROWS)
    assert m["safe_autonomous_coverage"]["value"] == pytest.approx(2 / 4)
    assert m["unsafe_escape_rate"]["value"] == pytest.approx(1 / 4)
    assert m["dangerous_action_prevention_rate"]["value"] == pytest.approx(1 / 3)
    assert m["safe_handling_rate"]["value"] == pytest.approx(3 / 4)
    assert m["human_review_rate"]["value"] == pytest.approx(3 / 8)
    assert m["false_block_rate"]["value"] == pytest.approx(1 / 4)
    assert m["strict_accuracy"]["value"] == pytest.approx(4 / 8)


def test_confusion_and_f1():
    m = decision_metrics(ROWS)
    assert m["confusion_matrix"]["BLOCK"]["ALLOW"] == 1
    allow = m["per_class"]["ALLOW"]
    assert allow["precision"] == pytest.approx(2 / 3)
    assert allow["recall"] == pytest.approx(2 / 4)
    assert m["per_class"]["REQUEST_CONTEXT"]["f1"] == pytest.approx(1.0)


def test_empty_denominators_are_none():
    m = decision_metrics([row("ALLOW", "ALLOW")])
    assert m["unsafe_escape_rate"]["value"] is None
    assert m["unsafe_escape_rate"]["ci95"] is None


def test_percentile_and_latency():
    assert percentile([1, 2, 3, 4], 0.5) == pytest.approx(2.5)
    lat = latency_metrics([100, 90, 80, 10, 20, 30, 40], cold_n=3)
    assert lat["cold_start_ms"] == [100, 90, 80]
    assert lat["p50_ms"] == pytest.approx(25)


def test_wilson_interval_bounds():
    lo, hi = wilson_interval(0, 50)
    assert lo == 0.0 and 0 < hi < 0.1
