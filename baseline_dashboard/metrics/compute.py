"""
compute.py
----------
Every number on the dashboard, derived from the two small modeled tables.

Two ideas are kept apart on purpose.

*The window is per user, not per calendar.* A user is included by acquisition
month; their orders are then counted over their own first 90 days, measured
from their own acquisition date. Filtering orders by calendar date instead
would give users acquired late in a month a shorter window and quietly
understate the metric.

*The cards describe one cohort month, the charts describe the range.* The
reference period selects a span of acquisition months; the KPI cards report the
most recent month in that span, compared against the month before it. The
charts plot every month in the span. Both come off one per-month table built
here, so a card and a bar can never disagree about the same month.
"""

from dataclasses import dataclass, field

import pandas as pd

# The observation window, in days from each user's own acquisition date. Day 0
# is the acquisition day, so the window is offsets 0..89. It is fixed: the
# dashboard used to offer 3/6/9/12 months, and no longer does.
WINDOW_DAYS = 90

WINDOW_LABEL = f"{WINDOW_DAYS}-Day"

# Columns of the per-month table, in display order.
COUNT_COLUMNS = (
    "acquired_users",
    "purchasing_customers",
    "total_orders",
    "total_gross_order_value",
)
RATIO_COLUMNS = (
    "conversion_rate",
    "orders_per_purchasing_customer",
    "average_order_value",
    "customer_value",
)


def _safe_divide(numerator: float, denominator: float) -> float:
    """Ratio, or NaN when the denominator is empty -- never a ZeroDivisionError."""
    return float(numerator) / denominator if denominator else float("nan")


@dataclass(frozen=True)
class CohortFilter:
    """The dashboard's one filter: which acquisition months are in scope."""

    start_month: pd.Period
    end_month: pd.Period

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


@dataclass(frozen=True)
class MonthMetrics:
    """One acquisition month, observed over each user's own first 90 days."""

    month: pd.Period

    acquired_users: int
    purchasing_customers: int
    total_orders: int
    total_gross_order_value: float

    conversion_rate: float
    orders_per_purchasing_customer: float
    average_order_value: float
    customer_value: float

    @property
    def label(self) -> str:
        return self.month.strftime("%b %Y")


@dataclass(frozen=True)
class CohortMetrics:
    """
    Everything the dashboard displays.

    The headline fields are the *latest* month in the reference period, not the
    period as a whole -- that is what the KPI cards show, and View Underlying
    Data reads the same fields so the two agree. `by_month` carries every month
    in the period for the charts.
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

    by_month: pd.DataFrame
    latest: MonthMetrics
    previous: MonthMetrics | None

    user_ids: tuple[str, ...] = field(repr=False, default=())

    @property
    def window_label(self) -> str:
        """'90-Day', the prefix every window-dependent metric name carries."""
        return WINDOW_LABEL

    @property
    def window_days(self) -> int:
        return WINDOW_DAYS

    @property
    def months(self) -> list[pd.Period]:
        """Acquisition months in the reference period, ascending."""
        return list(self.by_month.acquisition_month)

    def delta(self, attribute: str) -> float | None:
        """
        Change in one metric from the previous cohort month.

        None when there is no previous month -- the first cohort in the data
        has nothing to be compared against, and showing a delta of zero there
        would be a lie rather than a missing value.
        """
        if self.previous is None:
            return None
        current = getattr(self.latest, attribute)
        earlier = getattr(self.previous, attribute)
        if current != current or earlier != earlier:  # NaN on either side
            return None
        return float(current) - float(earlier)

    def delta_ratio(self, attribute: str) -> float | None:
        """Change as a fraction of the previous month, or None if undefined."""
        change = self.delta(attribute)
        if change is None:
            return None
        earlier = float(getattr(self.previous, attribute))
        if not earlier:
            return None
        return change / abs(earlier)


def _derive(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the three factors and the headline to a frame of the four counts."""
    frame = frame.copy()
    frame["conversion_rate"] = [
        _safe_divide(p, a)
        for p, a in zip(frame.purchasing_customers, frame.acquired_users)
    ]
    frame["orders_per_purchasing_customer"] = [
        _safe_divide(o, p)
        for o, p in zip(frame.total_orders, frame.purchasing_customers)
    ]
    frame["average_order_value"] = [
        _safe_divide(v, o)
        for v, o in zip(frame.total_gross_order_value, frame.total_orders)
    ]
    frame["customer_value"] = (
        frame.conversion_rate
        * frame.orders_per_purchasing_customer
        * frame.average_order_value
    )
    return frame


def month_table(customers: pd.DataFrame, window_facts: pd.DataFrame) -> pd.DataFrame:
    """
    One row per acquisition month in the data, over every user.

    Built across all months rather than only the selected ones, because the KPI
    comparison reaches one month back -- and the month before the reference
    period is still a real cohort, even when the filter excludes it.

    `window_facts` is already restricted to each user's first 90 days, so no
    windowing happens here.
    """
    totals = window_facts.set_index("user_id")
    orders = customers.user_id.map(totals.orders).fillna(0.0)
    gross = customers.user_id.map(totals.gross_value).fillna(0.0)

    frame = pd.DataFrame(
        {
            "acquisition_month": customers.acquisition_month.values,
            "purchased": (orders.values > 0).astype(int),
            "orders": orders.values,
            "gross_value": gross.values,
        }
    )
    grouped = frame.groupby("acquisition_month", sort=True).agg(
        acquired_users=("purchased", "size"),
        purchasing_customers=("purchased", "sum"),
        total_orders=("orders", "sum"),
        total_gross_order_value=("gross_value", "sum"),
    )
    grouped["total_orders"] = grouped.total_orders.astype("int64")
    grouped["acquired_users"] = grouped.acquired_users.astype("int64")
    grouped["purchasing_customers"] = grouped.purchasing_customers.astype("int64")

    return _derive(grouped.reset_index())


def _month_metrics(row: pd.Series) -> MonthMetrics:
    return MonthMetrics(
        month=row.acquisition_month,
        acquired_users=int(row.acquired_users),
        purchasing_customers=int(row.purchasing_customers),
        total_orders=int(row.total_orders),
        total_gross_order_value=float(row.total_gross_order_value),
        conversion_rate=float(row.conversion_rate),
        orders_per_purchasing_customer=float(row.orders_per_purchasing_customer),
        average_order_value=float(row.average_order_value),
        customer_value=float(row.customer_value),
    )


def compute(
    customers: pd.DataFrame,
    window_facts: pd.DataFrame,
    cohort: CohortFilter,
) -> CohortMetrics:
    """
    Compute everything the dashboard shows for one reference period.

    `customers` needs acquisition_month (period) and user_id.
    `window_facts` needs user_id, orders, gross_value -- already windowed to
    each user's first 90 days.
    """
    table = month_table(customers, window_facts)
    in_range = table[
        table.acquisition_month.between(cohort.start_month, cohort.end_month)
    ].reset_index(drop=True)

    if in_range.empty:
        empty = MonthMetrics(
            month=cohort.end_month,
            acquired_users=0,
            purchasing_customers=0,
            total_orders=0,
            total_gross_order_value=0.0,
            conversion_rate=float("nan"),
            orders_per_purchasing_customer=float("nan"),
            average_order_value=float("nan"),
            customer_value=float("nan"),
        )
        return CohortMetrics(
            cohort=cohort,
            acquired_users=0,
            purchasing_customers=0,
            total_orders=0,
            total_gross_order_value=0.0,
            conversion_rate=float("nan"),
            orders_per_purchasing_customer=float("nan"),
            average_order_value=float("nan"),
            customer_value=float("nan"),
            by_month=in_range,
            latest=empty,
            previous=None,
            user_ids=(),
        )

    latest_month = in_range.acquisition_month.iloc[-1]
    latest = _month_metrics(in_range.iloc[-1])

    # The comparison reaches one month back through the *whole* dataset, not
    # just the selection: a single-month reference period should still show a
    # change, and the month before it is a real cohort either way.
    position = int(table.index[table.acquisition_month == latest_month][0])
    previous = _month_metrics(table.iloc[position - 1]) if position > 0 else None

    latest_users = customers.user_id[customers.acquisition_month == latest_month]

    return CohortMetrics(
        cohort=cohort,
        acquired_users=latest.acquired_users,
        purchasing_customers=latest.purchasing_customers,
        total_orders=latest.total_orders,
        total_gross_order_value=latest.total_gross_order_value,
        conversion_rate=latest.conversion_rate,
        orders_per_purchasing_customer=latest.orders_per_purchasing_customer,
        average_order_value=latest.average_order_value,
        customer_value=latest.customer_value,
        by_month=in_range,
        latest=latest,
        previous=previous,
        user_ids=tuple(sorted(latest_users)),
    )


def chart_frame(metrics: CohortMetrics) -> pd.DataFrame:
    """
    Both charts' series in one tidy frame, so they cannot drift apart.

    Carries `is_latest` so a chart can pick out the month the KPI cards are
    reporting -- without it, nothing on screen connects the cards to the bars.
    """
    frame = metrics.by_month.copy()
    frame["month_label"] = [
        month.strftime("%b %Y") for month in frame.acquisition_month
    ]
    frame["sort_key"] = [month.ordinal for month in frame.acquisition_month]
    frame["is_latest"] = frame.acquisition_month == metrics.latest.month
    return frame.drop(columns="acquisition_month")
