"""
checks.py
---------
The consistency checks required by the spec, run at data load and after every
filter change.

The dashboard's purpose is to let someone verify a metric by hand. If the
headline disagreed with its own components, or with the charts underneath it,
the study task would be measuring a bug rather than a participant. These
assertions make that failure loud instead of subtle.
"""

from dataclasses import dataclass

import numpy as np

from metrics.compute import CohortMetrics

# Money is rounded to cents at build time, so equality here is approximate by
# construction. A tenth of a cent is far tighter than any displayed precision.
TOLERANCE = 1e-3


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _close(a: float, b: float) -> bool:
    if np.isnan(a) and np.isnan(b):
        return True
    return bool(np.isclose(a, b, rtol=TOLERANCE, atol=TOLERANCE))


def run_checks(metrics: CohortMetrics) -> list[CheckResult]:
    """Return one result per required check, in spec order."""
    headline = metrics.customer_value

    product = (
        metrics.conversion_rate
        * metrics.orders_per_purchasing_customer
        * metrics.average_order_value
    )
    simplified = (
        metrics.total_gross_order_value / metrics.acquired_users
        if metrics.acquired_users
        else float("nan")
    )
    cumulative_final = (
        float(metrics.cumulative_value.iloc[-1])
        if len(metrics.cumulative_value)
        else float("nan")
    )
    monthly_sum = float(metrics.monthly_contribution.sum())

    return [
        CheckResult(
            "headline == conversion x orders x AOV",
            _close(headline, product),
            f"{headline:.6f} vs {product:.6f}",
        ),
        CheckResult(
            "headline == total gross value / acquired users",
            _close(headline, simplified),
            f"{headline:.6f} vs {simplified:.6f}",
        ),
        CheckResult(
            f"cumulative month {metrics.cohort.window} == headline",
            _close(cumulative_final, headline),
            f"{cumulative_final:.6f} vs {headline:.6f}",
        ),
        CheckResult(
            "sum of monthly contributions == headline",
            _close(monthly_sum, headline),
            f"{monthly_sum:.6f} vs {headline:.6f}",
        ),
    ]


def assert_consistent(metrics: CohortMetrics) -> list[CheckResult]:
    """Run the checks and raise if any fail."""
    results = run_checks(metrics)
    failed = [r for r in results if not r.passed]
    if failed:
        details = "\n".join(f"  - {r.name}: {r.detail}" for r in failed)
        raise AssertionError(
            f"Metric consistency failed for {metrics.cohort.label} "
            f"({metrics.cohort.window}-month window):\n{details}"
        )
    return results
