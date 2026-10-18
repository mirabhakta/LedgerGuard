from decimal import Decimal

from backend.app.services.feature_calculator import (
    calculate_amount_features,
    historical_amount_stats,
)


def test_decimal_population_statistics_and_features() -> None:
    values = [Decimal("10.00"), Decimal("20.00"), Decimal("30.00")]
    stats = historical_amount_stats(values)
    assert stats.observation_count == 3
    assert stats.mean == Decimal("20.00")
    assert stats.median == Decimal("20.00")
    assert stats.minimum == Decimal("10.00")
    assert stats.maximum == Decimal("30.00")
    assert stats.stddev.quantize(Decimal("0.0001")) == Decimal("8.1650")
    features = calculate_amount_features(Decimal("30.00"), stats, values)
    assert features["ratio_to_mean"] == "1.5"
    assert features["empirical_percentile"] == "1"


def test_empty_singleton_and_zero_denominator_are_explicit() -> None:
    empty = historical_amount_stats([])
    assert empty.mean is None and empty.stddev is None
    singleton = historical_amount_stats([Decimal("0")])
    assert singleton.stddev is None
    features = calculate_amount_features(Decimal("10"), singleton, [Decimal("0")])
    assert features["ratio_to_mean"] is None
    assert features["z_score"] is None
