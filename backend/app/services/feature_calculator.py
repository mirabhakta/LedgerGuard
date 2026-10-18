"""Decimal-safe deterministic feature calculations."""

from __future__ import annotations

from decimal import Decimal, localcontext

from backend.app.models.state import HistoricalAmountStats


def historical_amount_stats(amounts: list[Decimal]) -> HistoricalAmountStats:
    values = sorted(amounts)
    count = len(values)
    if not values:
        return HistoricalAmountStats(observation_count=0)
    total = sum(values, Decimal("0"))
    mean = total / Decimal(count)
    middle = count // 2
    median = (
        values[middle]
        if count % 2
        else (values[middle - 1] + values[middle]) / Decimal("2")
    )
    stddev: Decimal | None = None
    if count >= 2:
        with localcontext() as context:
            context.prec = 28
            variance = sum((value - mean) ** 2 for value in values) / Decimal(count)
            stddev = variance.sqrt()
    return HistoricalAmountStats(
        observation_count=count,
        mean=mean,
        median=median,
        stddev=stddev,
        minimum=values[0],
        maximum=values[-1],
    )


def calculate_amount_features(
    amount: Decimal, stats: HistoricalAmountStats, history: list[Decimal]
) -> dict[str, object]:
    mean = stats.mean
    median = stats.median
    stddev = stats.stddev
    less_or_equal = sum(1 for value in history if value <= amount)
    return {
        "amount": str(amount),
        "history_count": stats.observation_count,
        "absolute_deviation_from_mean": str(abs(amount - mean)) if mean is not None else None,
        "absolute_deviation_from_median": (
            str(abs(amount - median)) if median is not None else None
        ),
        "ratio_to_mean": str(amount / mean) if mean not in (None, Decimal("0")) else None,
        "ratio_to_median": (
            str(amount / median) if median not in (None, Decimal("0")) else None
        ),
        "z_score": (
            str((amount - mean) / stddev)
            if mean is not None and stddev not in (None, Decimal("0"))
            else None
        ),
        "empirical_percentile": (
            str(Decimal(less_or_equal) / Decimal(len(history))) if history else None
        ),
    }
