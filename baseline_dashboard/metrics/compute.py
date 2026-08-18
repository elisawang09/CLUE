"""
compute.py
----------
Every number on the dashboard, derived from the two small modeled tables.

The reference acquisition period decides *which* users are included; the
observation window decides *how long each one is observed after their own
acquisition date*. Those are separate concerns, and conflating them is the
mistake this module exists to avoid: filtering orders by calendar date would
give users acquired late in the period a shorter window and quietly understate
the metric.
"""

from dataclasses import dataclass, field

import pandas as pd

DEFAULT_WINDOW = 6
WINDOW_CHOICES: tuple[int, ...] = (3, 6, 9, 12)


def _safe_divide(numerator: float, denominator: float) -> float:
    """Ratio, or NaN when the denominator is empty -- never a ZeroDivisionError."""
    return float(numerator) / denominator if denominator else float("nan")


@dataclass(frozen=True)
class CohortFilter:
    """The dashboard's two filters."""

    start_month: pd.Period
    end_month: pd.Period
    window: int = DEFAULT_WINDOW

    @property
    def label(self) -> str:
        """Human-readable period, e.g. 'Jan-Mar 2022' or 'Feb 2022'."""
        if self.start_month == self.end_month:
            return self.start_month.strftime("%b %Y")
        if self.start_month.year == self.end_month.year:
            return (
                f"{self.start_month.strftime('%b')}-"
                f"{self.end_month.strftime('%b %Y')}"
            )
        return (
            f"{self.start_month.strftime('%b %Y')}-"
            f"{self.end_month.strftime('%b %Y')}"
        )

    @property
    def months(self) -> list[int]:
        """Age months 1..window, the x-axis of both charts."""
        return list(range(1, self.window + 1))


@dataclass(frozen=True)
class CohortMetrics:
    """
    Everything the dashboard displays for one (reference period, window).

    `monthly_contribution` and `cumulative_value` are indexed by age month; the
    cumulative series is the running sum of the monthly one, never computed
    separately, so the two charts can never disagree.
    """

    cohort: CohortFilter

    acquired_users: int
    purchasing_customers: int
    total_orders: int
    total_gross_order_value: float

    conversion_rate: float
    orders_per_purchasing_customer: float
    average_order_value: float
    customer_value: float

    monthly_contribution: pd.Series
    cumulative_value: pd.Series

    user_ids: tuple[str, ...] = field(repr=False, default=())

    @property
    def window_label(self) -> str:
        """'6-Month', used to build metric names that follow the filter."""
        return f"{self.cohort.window}-Month"


def compute(
    customers: pd.DataFrame,
    age_facts: pd.DataFrame,
    cohort: CohortFilter,
) -> CohortMetrics:
    """
    Compute all metrics for one reference period and observation window.

    `customers` needs acquisition_month (period), user_id, is_purchaser.
    `age_facts` needs user_id, customer_age_month, orders, gross_value.
    """
    in_period = customers[
        customers.acquisition_month.between(cohort.start_month, cohort.end_month)
    ]
    acquired_ids = set(in_period.user_id)
    acquired_users = len(acquired_ids)

    observed = age_facts[
        age_facts.user_id.isin(acquired_ids)
        & age_facts.customer_age_month.between(1, cohort.window)
    ]

    purchasing_customers = observed.user_id.nunique()
    total_orders = int(observed.orders.sum())
    total_gross_order_value = float(observed.gross_value.sum())

    # Value generated in each month since acquisition, spread over everyone
    # acquired -- including those who never purchased, which is what makes this
    # "per acquired user" rather than "per customer".
    by_month = (
        observed.groupby("customer_age_month").gross_value.sum()
        .reindex(cohort.months, fill_value=0.0)
    )
    monthly_contribution = (
        by_month / acquired_users if acquired_users else by_month * float("nan")
    )
    monthly_contribution.index.name = "customer_age_month"

    conversion_rate = _safe_divide(purchasing_customers, acquired_users)
    orders_per_purchasing_customer = _safe_divide(total_orders, purchasing_customers)
    average_order_value = _safe_divide(total_gross_order_value, total_orders)

    return CohortMetrics(
        cohort=cohort,
        acquired_users=acquired_users,
        purchasing_customers=purchasing_customers,
        total_orders=total_orders,
        total_gross_order_value=total_gross_order_value,
        conversion_rate=conversion_rate,
        orders_per_purchasing_customer=orders_per_purchasing_customer,
        average_order_value=average_order_value,
        customer_value=conversion_rate
        * orders_per_purchasing_customer
        * average_order_value,
        monthly_contribution=monthly_contribution,
        cumulative_value=monthly_contribution.cumsum(),
        user_ids=tuple(sorted(acquired_ids)),
    )


def chart_frame(metrics: CohortMetrics) -> pd.DataFrame:
    """Both chart series in one tidy frame, so they cannot drift apart."""
    return pd.DataFrame(
        {
            "customer_age_month": metrics.cohort.months,
            "month_label": [f"Month {k}" for k in metrics.cohort.months],
            "monthly_contribution": metrics.monthly_contribution.values,
            "cumulative_value": metrics.cumulative_value.values,
        }
    )
