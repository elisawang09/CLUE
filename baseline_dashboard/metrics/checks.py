"""
checks.py
---------
The consistency checks required by the spec, run at data load and after every
filter change.

The dashboard's purpose is to let someone verify a metric by hand. If the
headline disagreed with its own components, or with the charts underneath it,
the study task would be measuring a bug rather than a participant. These
assertions make that failure loud instead of subtle.

The cards report one acquisition month and the charts report every month in the
reference period, so the checks cover both: the headline against its own
factors, and every charted month against the same two identities.
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

    results = [
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
    ]

    # The cards report one month and the charts report every month in the
    # period, off the same table. If a bar ever disagreed with the card for the
    # same month, a participant reading both would be reading a bug.
    by_month = metrics.by_month
    if not by_month.empty:
        row = by_month.iloc[-1]
        results.append(
            CheckResult(
                "cards report the latest month in the period",
                _close(float(row.customer_value), headline)
                and int(row.acquired_users) == metrics.acquired_users,
                f"{row.acquisition_month} {float(row.customer_value):.6f} vs "
                f"{metrics.latest.month} {headline:.6f}",
            )
        )

        per_month_product = (
            by_month.conversion_rate
            * by_month.orders_per_purchasing_customer
            * by_month.average_order_value
        )
        worst = float(
            (by_month.customer_value - per_month_product).abs().max()
        )
        results.append(
            CheckResult(
                "every charted month == conversion x orders x AOV",
                worst <= TOLERANCE,
                f"largest disagreement {worst:.9f} across "
                f"{len(by_month)} month(s)",
            )
        )

        acquired = by_month.acquired_users
        gross = by_month.total_gross_order_value
        simplified_month = [
            value / users if users else float("nan")
            for value, users in zip(gross, acquired)
        ]
        worst_simplified = max(
            (
                abs(a - b)
                for a, b in zip(by_month.customer_value, simplified_month)
                if a == a and b == b
            ),
            default=0.0,
        )
        results.append(
            CheckResult(
                "every charted month == gross value / acquired users",
                worst_simplified <= TOLERANCE,
                f"largest disagreement {worst_simplified:.9f} across "
                f"{len(by_month)} month(s)",
            )
        )

    return results


def assert_consistent(metrics: CohortMetrics) -> list[CheckResult]:
    """Run the checks and raise if any fail."""
    results = run_checks(metrics)
    failed = [r for r in results if not r.passed]
    if failed:
        details = "\n".join(f"  - {r.name}: {r.detail}" for r in failed)
        raise AssertionError(
            f"Metric consistency failed for {metrics.cohort.label} "
            f"({metrics.window_label} window):\n{details}"
        )
    return results
