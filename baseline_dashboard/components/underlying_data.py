"""
underlying_data.py
------------------
View Underlying Data: the rows behind the number.

Two levels, matching how a BI tool exposes a mark:
  Summary          -- the selected mark at its own level of aggregation
  Underlying rows  -- records from the dashboard's data source that fed it

The tables are for reading, not for taking away: there is no CSV export, so
whatever a participant works out here they work out on screen.

It shows the modeled data source and stops there. No joins, no SQL, no upstream
pipeline -- reconstructing the ETL is exactly what this conventional dashboard
is not for.

Which grain opens first follows the metric: user-level metrics land on one row
per acquired user, order-value metrics on one row per order.

The rows are scoped to the cohort month the KPI cards report, not to the whole
reference period, so they add up to the number on the card that opened them.
"""

import pandas as pd
import streamlit as st

from components.charts import month_summary
from datasource.loader import load_customers, load_orders, load_window_facts
from metrics.compute import WINDOW_DAYS, CohortMetrics
from metrics.registry import METRICS, ORDER_ITEM_GRAIN, PRIMARY_ID
from study.events import log_if_changed
from study.session import resolve_session

DEFAULT_ROWS = 200

CUSTOMER_GRAIN_LABEL = "One row per acquired user"
ORDER_GRAIN_LABEL = "One row per order"


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def customer_rows(metrics: CohortMetrics) -> pd.DataFrame:
    """
    One row per acquired user, including those who never ordered.

    The non-purchasers are the point: they are what makes the headline "per
    acquired user" rather than "per customer", and a participant checking the
    conversion rate needs to see them.
    """
    customers = load_customers()
    totals = load_window_facts().set_index("user_id")

    in_period = customers[customers.user_id.isin(set(metrics.user_ids))]

    rows = pd.DataFrame(
        {
            "user_id": in_period.user_id.values,
            "acquisition_date": in_period.account_created_at.dt.date.values,
        }
    )
    rows[f"orders_{WINDOW_DAYS}d"] = (
        rows.user_id.map(totals.orders).fillna(0).astype(int)
    )
    rows[f"gross_value_{WINDOW_DAYS}d"] = (
        rows.user_id.map(totals.gross_value).fillna(0.0).round(2)
    )
    rows.insert(
        2,
        f"purchasing_customer_{WINDOW_DAYS}d",
        (rows[f"orders_{WINDOW_DAYS}d"] > 0).astype(int),
    )
    return rows.sort_values("acquisition_date", ignore_index=True)


def order_rows(metrics: CohortMetrics) -> pd.DataFrame:
    """
    One row per qualifying order.

    No month argument any more: the selected acquisition month already decides
    which users are in scope, and every order shown is inside that user's own
    90-day window.
    """
    orders = load_orders(metrics.user_ids)

    acquired_at = load_customers().set_index("user_id").account_created_at
    rows = pd.DataFrame(
        {
            "order_id": orders.order_id.values,
            "user_id": orders.user_id.values,
            "acquisition_date": orders.user_id.map(acquired_at).dt.date.values,
            "days_since_acquisition": orders.customer_age_day.values,
            "revenue": orders.revenue.values,
            "cost": orders.cost.values,
            "gross_value": orders.gross_value.values,
        }
    )
    return rows.sort_values(
        ["user_id", "days_since_acquisition"], ignore_index=True
    )


def period_summary(metrics: CohortMetrics) -> pd.DataFrame:
    """The cohort at the dashboard's own level of aggregation."""
    return pd.DataFrame(
        {
            "Acquisition Month": [metrics.latest.label],
            "Acquired Users": [metrics.acquired_users],
            "Purchasing Customers": [metrics.purchasing_customers],
            "Total Orders": [metrics.total_orders],
            "Total Gross Order Value": [metrics.total_gross_order_value],
            f"{metrics.window_label} Customer Value": [metrics.customer_value],
        }
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_summary(metrics: CohortMetrics, selected_month: str | None) -> None:
    st.caption("The selected marks at the level the dashboard aggregates them.")
    summary = period_summary(metrics)
    st.dataframe(
        summary,
        hide_index=True,
        width="stretch",
        column_config={
            "Total Gross Order Value": st.column_config.NumberColumn(format="$%.2f"),
            f"{metrics.window_label} Customer Value": st.column_config.NumberColumn(
                format="$%.2f"
            ),
        },
    )

    if selected_month is not None:
        detail = month_summary(metrics, selected_month)
        if not detail.empty:
            st.markdown(f"**Selected month — {selected_month}**")
            st.dataframe(
                detail,
                hide_index=True,
                width="stretch",
                column_config={
                    f"{metrics.window_label} Customer Value":
                        st.column_config.NumberColumn(format="$%.2f"),
                    f"{metrics.window_label} Purchase Conversion Rate":
                        st.column_config.NumberColumn(format="%.1f%%"),
                },
            )


def _render_rows(metrics: CohortMetrics, metric_id: str) -> None:
    default_grain = (
        ORDER_GRAIN_LABEL
        if METRICS[metric_id].grain == ORDER_ITEM_GRAIN
        else CUSTOMER_GRAIN_LABEL
    )
    options = [CUSTOMER_GRAIN_LABEL, ORDER_GRAIN_LABEL]

    grain = st.radio(
        "Level of detail",
        options,
        index=options.index(default_grain),
        horizontal=True,
        key="underlying_grain",
    )
    log_if_changed(
        "underlying_grain", "_logged_grain", grain, resolve_session(), metric=metric_id
    )

    if grain == CUSTOMER_GRAIN_LABEL:
        frame = customer_rows(metrics)
        caption = (
            f"Every user acquired {metrics.latest.label}, with their orders and "
            f"gross value over their first {WINDOW_DAYS} days. Users who never "
            f"ordered appear with zeros."
        )
        money_columns = [f"gross_value_{WINDOW_DAYS}d"]
    else:
        frame = order_rows(metrics)
        caption = (
            f"Every order placed by these users within their first "
            f"{WINDOW_DAYS} days. gross_value is revenue − cost, and "
            f"days_since_acquisition counts from each user's own signup day."
        )
        money_columns = ["revenue", "cost", "gross_value"]

    st.caption(caption)

    shown = st.number_input(
        "Rows to display",
        min_value=10,
        max_value=max(len(frame), 10),
        value=min(DEFAULT_ROWS, max(len(frame), 10)),
        step=50,
        key="underlying_row_count",
    )
    st.dataframe(
        frame.head(int(shown)),
        hide_index=True,
        width="stretch",
        height=340,
        column_config={
            column: st.column_config.NumberColumn(format="$%.2f")
            for column in money_columns
        },
    )
    st.caption(f"Showing {min(int(shown), len(frame)):,} of {len(frame):,} rows.")


@st.dialog("View Underlying Data", width="large")
def render_underlying_data(metrics: CohortMetrics) -> None:
    nav: list[str] = st.session_state.metric_nav
    metric_id = nav[-1] if nav else PRIMARY_ID
    selected_month = st.session_state.get("selected_cohort_month")

    st.markdown(f"### {METRICS[metric_id].name(metrics)}")
    scope = f" · {selected_month} selected on a chart" if selected_month else ""
    st.caption(
        f"Users acquired {metrics.latest.label} · first {WINDOW_DAYS} days{scope}"
    )

    summary_tab, rows_tab = st.tabs(["Summary", "Underlying rows"])
    with summary_tab:
        _render_summary(metrics, selected_month)
    with rows_tab:
        _render_rows(metrics, metric_id)

    st.divider()
    _, close_col = st.columns([1, 1])

    if close_col.button("Close", key="underlying_close"):
        st.session_state.open_panel = None
        st.rerun()
