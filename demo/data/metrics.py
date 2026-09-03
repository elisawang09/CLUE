"""
metrics.py
----------
Every number CLUE displays, computed from the modeled data source.

The metric is **6-Month Customer Value**: the average value generated per
acquired user during the first 6 months after acquisition. It is observed
history, not a prediction.

Two time windows are involved and they are deliberately not merged:

  - the *reference acquisition period* decides which users are in the group;
  - the *six-month observation window* is measured from each user's own
    acquisition date, so a user acquired late in the period still gets six
    months of follow-up.

Filtering orders by calendar date instead would quietly understate the metric.

The reference period is pinned to the baseline dashboard's default so a
participant handed over by "Open in CLUE" sees the same figures they just left.
CLUE reads the same Parquet tables the dashboard does, but shares no code with
it -- the two apps stay import-independent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Reference acquisition period and observation window
# ---------------------------------------------------------------------------
#
# Matches baseline_dashboard/components/filters.py: the largest 3-month
# acquisition window in the data, fully matured (every included user has six
# months of follow-up available).

REFERENCE_START = pd.Period("2022-01", freq="M")
REFERENCE_END = pd.Period("2022-03", freq="M")
OBSERVATION_MONTHS = 6

# Only the two small tables are read; the million-row order tables are not
# needed for any number on the main view.
_DEFAULT_MODELED_DIR = (
    Path(__file__).resolve().parents[2] / "baseline_dashboard" / "data" / "modeled"
)


def modeled_dir() -> Path:
    """Where the modeled Parquet tables live. Override with CLUE_MODELED_DIR."""
    override = os.environ.get("CLUE_MODELED_DIR")
    return Path(override) if override else _DEFAULT_MODELED_DIR


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def money(value: float) -> str:
    return f"${value:,.2f}" if abs(value) < 1000 else f"${value:,.0f}"


def whole_money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1%}"


def count(value: float) -> str:
    return f"{value:,.0f}"


def decimal(value: float) -> str:
    return f"{value:,.1f}"


def md(text: str) -> str:
    """
    Escape a formatted value for st.markdown.

    Streamlit reads text between two `$` as LaTeX, so a line carrying two money
    values renders as maths with the markup showing through. Escaping the
    dollar signs is the fix; HTML blocks are unaffected and do not need this.
    """
    return text.replace("$", r"\$")


def period_label(start: pd.Period, end: pd.Period) -> str:
    """Human-readable acquisition period, e.g. 'Jan-Mar 2022'."""
    if start == end:
        return start.strftime("%b %Y")
    if start.year == end.year:
        return f"{start.strftime('%b')}-{end.strftime('%b %Y')}"
    return f"{start.strftime('%b %Y')}-{end.strftime('%b %Y')}"


# ---------------------------------------------------------------------------
# Baseline metrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BaselineMetrics:
    """
    The observed historical baseline for one reference group.

    Series are plain tuples rather than pandas objects so the whole record
    stays cheap to cache and compare.
    """

    acquired_users: int
    purchasing_customers: int
    total_orders: int
    total_gross_order_value: float

    conversion_rate: float
    orders_per_purchasing_customer: float
    average_order_value: float
    customer_value: float

    monthly_contribution: tuple[float, ...]
    cumulative_value: tuple[float, ...]

    period_label: str
    window: int = OBSERVATION_MONTHS
    is_fallback: bool = False

    @property
    def window_label(self) -> str:
        """'6-Month', the prefix every window-dependent metric name carries."""
        return f"{self.window}-Month"

    @property
    def months(self) -> list[int]:
        """Age months 1..window, relative to each user's own acquisition date."""
        return list(range(1, self.window + 1))


def _safe_divide(numerator: float, denominator: float) -> float:
    """Ratio, or NaN when the denominator is empty -- never a ZeroDivisionError."""
    return float(numerator) / denominator if denominator else float("nan")


def _from_totals(
    acquired_users: int,
    purchasing_customers: int,
    total_orders: int,
    total_gross_order_value: float,
    monthly_gross_value: list[float],
    label: str,
    is_fallback: bool = False,
) -> BaselineMetrics:
    """Derive the three factors and the headline from the four base counts."""
    conversion_rate = _safe_divide(purchasing_customers, acquired_users)
    orders_per_purchasing_customer = _safe_divide(total_orders, purchasing_customers)
    average_order_value = _safe_divide(total_gross_order_value, total_orders)

    # Value generated in each month since acquisition, spread over everyone
    # acquired -- including users who never purchased, which is what makes this
    # "per acquired user" rather than "per customer".
    monthly = [
        _safe_divide(value, acquired_users) for value in monthly_gross_value
    ]
    cumulative: list[float] = []
    running = 0.0
    for value in monthly:
        running += value
        cumulative.append(running)

    return BaselineMetrics(
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
        monthly_contribution=tuple(monthly),
        cumulative_value=tuple(cumulative),
        period_label=label,
        is_fallback=is_fallback,
    )


# Used when the modeled data source has not been built, so the demo still runs
# standalone. These are the spec's shared reference example figures; every
# displayed metric is still derived from them rather than written out.
_FALLBACK_TOTALS = dict(
    acquired_users=3_000,
    purchasing_customers=1_200,
    total_orders=6_000,
    total_gross_order_value=312_000.0,
    monthly_gross_value=[52_000.0] * OBSERVATION_MONTHS,
    label="the reference acquisition period",
)


def compute_baseline() -> BaselineMetrics:
    """
    Compute the historical baseline from the modeled tables.

    Falls back to the spec's reference example when the data source has not
    been built. Plain function, no Streamlit dependency, so it can be checked
    from a shell.
    """
    directory = modeled_dir()
    customers_path = directory / "customers.parquet"
    age_facts_path = directory / "customer_age_facts.parquet"

    if not (customers_path.exists() and age_facts_path.exists()):
        return _from_totals(**_FALLBACK_TOTALS, is_fallback=True)

    customers = pd.read_parquet(
        customers_path, columns=["user_id", "acquisition_month"]
    )
    acquisition_month = pd.PeriodIndex(customers.acquisition_month, freq="M")

    # Step 1: who belongs to the reference group.
    acquired_ids = set(
        customers.user_id[
            (acquisition_month >= REFERENCE_START) & (acquisition_month <= REFERENCE_END)
        ]
    )

    age_facts = pd.read_parquet(
        age_facts_path,
        columns=["user_id", "customer_age_month", "orders", "gross_value"],
    )

    # Step 2: their orders, windowed against each user's own acquisition date.
    observed = age_facts[
        age_facts.user_id.isin(acquired_ids)
        & age_facts.customer_age_month.between(1, OBSERVATION_MONTHS)
    ]

    months = list(range(1, OBSERVATION_MONTHS + 1))
    by_month = (
        observed.groupby("customer_age_month").gross_value.sum()
        .reindex(months, fill_value=0.0)
    )

    return _from_totals(
        acquired_users=len(acquired_ids),
        purchasing_customers=int(observed.user_id.nunique()),
        total_orders=int(observed.orders.sum()),
        total_gross_order_value=float(observed.gross_value.sum()),
        monthly_gross_value=[float(value) for value in by_month],
        label=period_label(REFERENCE_START, REFERENCE_END),
    )


@st.cache_data(show_spinner=False)
def load_baseline() -> BaselineMetrics:
    """Cached baseline, parsed once per server process."""
    return compute_baseline()


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------

# Money is rounded to cents at build time, so equality here is approximate by
# construction. A tenth of a cent is tighter than any displayed precision.
TOLERANCE = 1e-3


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _close(a: float, b: float) -> bool:
    if a != a and b != b:  # both NaN
        return True
    return abs(a - b) <= TOLERANCE + TOLERANCE * abs(b)


def run_checks(baseline: BaselineMetrics) -> list[CheckResult]:
    """
    Assert the metric agrees with itself.

    If the headline ever disagreed with its own components, a study task would
    be measuring a bug rather than a participant, so these are surfaced in the
    UI rather than logged quietly.
    """
    headline = baseline.customer_value
    product = (
        baseline.conversion_rate
        * baseline.orders_per_purchasing_customer
        * baseline.average_order_value
    )
    simplified = _safe_divide(
        baseline.total_gross_order_value, baseline.acquired_users
    )
    cumulative_final = (
        baseline.cumulative_value[-1] if baseline.cumulative_value else float("nan")
    )

    return [
        CheckResult(
            "6-Month Customer Value == conversion x orders per customer x AOV",
            _close(headline, product),
            f"{headline:.6f} vs {product:.6f}",
        ),
        CheckResult(
            "6-Month Customer Value == total gross order value / acquired users",
            _close(headline, simplified),
            f"{headline:.6f} vs {simplified:.6f}",
        ),
        CheckResult(
            "Purchasing Customers == acquired users x conversion rate",
            _close(
                baseline.purchasing_customers,
                baseline.acquired_users * baseline.conversion_rate,
            ),
            f"{baseline.purchasing_customers} vs "
            f"{baseline.acquired_users * baseline.conversion_rate:.6f}",
        ),
        CheckResult(
            "Total Orders == purchasing customers x orders per customer",
            _close(
                baseline.total_orders,
                baseline.purchasing_customers
                * baseline.orders_per_purchasing_customer,
            ),
            f"{baseline.total_orders} vs "
            f"{baseline.purchasing_customers * baseline.orders_per_purchasing_customer:.6f}",
        ),
        CheckResult(
            "Total Gross Order Value == total orders x AOV",
            _close(
                baseline.total_gross_order_value,
                baseline.total_orders * baseline.average_order_value,
            ),
            f"{baseline.total_gross_order_value:.6f} vs "
            f"{baseline.total_orders * baseline.average_order_value:.6f}",
        ),
        CheckResult(
            f"Cumulative month {baseline.window} == 6-Month Customer Value",
            _close(cumulative_final, headline),
            f"{cumulative_final:.6f} vs {headline:.6f}",
        ),
    ]


def failed_checks(baseline: BaselineMetrics) -> list[CheckResult]:
    """Only the checks that did not pass, for the UI banner."""
    return [check for check in run_checks(baseline) if not check.passed]


# ---------------------------------------------------------------------------
# Values keyed by provenance node id
# ---------------------------------------------------------------------------

def node_values(baseline: BaselineMetrics) -> dict[str, str]:
    """Formatted value for each provenance node, for labels and tooltips."""
    return {
        "cust_val": money(baseline.customer_value),
        "conv_rate": percent(baseline.conversion_rate),
        "orders_per_cust": decimal(baseline.orders_per_purchasing_customer),
        "avg_order_val": money(baseline.average_order_value),
        "acq_users": count(baseline.acquired_users),
        "purch_cust_1": count(baseline.purchasing_customers),
        "purch_cust_2": count(baseline.purchasing_customers),
        "tot_orders_1": count(baseline.total_orders),
        "tot_orders_2": count(baseline.total_orders),
        "tot_gross_val": whole_money(baseline.total_gross_order_value),
    }
