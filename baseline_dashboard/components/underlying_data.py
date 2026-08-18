"""
underlying_data.py
------------------
View Underlying Data: the rows behind the number.

Two levels, matching how a BI tool exposes a mark:
  Summary          -- the selected mark at its own level of aggregation
  Underlying rows  -- records from the dashboard's data source that fed it

It shows the modeled data source and stops there. No joins, no SQL, no upstream
pipeline -- reconstructing the ETL is exactly what this conventional dashboard
is not for.

Which grain opens first follows the metric: user-level metrics land on one row
per acquired user, order-value metrics on one row per order.
"""

import pandas as pd
import streamlit as st

from components.charts import month_summary
from datasource.loader import load_age_facts, load_customers, load_orders
from metrics.compute import CohortMetrics
from metrics.registry import METRICS, ORDER_ITEM_GRAIN, PRIMARY_ID
from study.events import log_event, log_if_changed
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
    window = metrics.cohort.window
    customers = load_customers()
    facts = load_age_facts()

    in_period = customers[customers.user_id.isin(set(metrics.user_ids))]
    observed = facts[
        facts.user_id.isin(set(metrics.user_ids))
        & facts.customer_age_month.between(1, window)
    ]
    per_user = observed.groupby("user_id").agg(
        orders=("orders", "sum"), gross_value=("gross_value", "sum")
    )

    rows = pd.DataFrame(
        {
            "user_id": in_period.user_id.values,
            "acquisition_date": in_period.account_created_at.dt.date.values,
        }
    )
    rows[f"orders_{window}m"] = (
        rows.user_id.map(per_user.orders).fillna(0).astype(int)
    )
    rows[f"gross_value_{window}m"] = (
        rows.user_id.map(per_user.gross_value).fillna(0.0).round(2)
    )
    rows.insert(
        2,
        f"purchasing_customer_{window}m",
        (rows[f"orders_{window}m"] > 0).astype(int),
    )
    return rows.sort_values("acquisition_date", ignore_index=True)


def order_rows(metrics: CohortMetrics, age_month: int | None) -> pd.DataFrame:
    """One row per qualifying order, optionally narrowed to one age month."""
    window = metrics.cohort.window
    orders = load_orders(metrics.user_ids, window)
    if age_month is not None:
        orders = orders[orders.customer_age_month == age_month]

    acquired_at = load_customers().set_index("user_id").account_created_at
    rows = pd.DataFrame(
        {
            "order_id": orders.order_id.values,
            "user_id": orders.user_id.values,
            "acquisition_date": orders.user_id.map(acquired_at).dt.date.values,
            "customer_age_month": orders.customer_age_month.values,
            "revenue": orders.revenue.values,
            "cost": orders.cost.values,
            "gross_value": orders.gross_value.values,
        }
    )
    return rows.sort_values(["user_id", "customer_age_month"], ignore_index=True)


def period_summary(metrics: CohortMetrics) -> pd.DataFrame:
    """The cohort at the dashboard's own level of aggregation."""
    return pd.DataFrame(
        {
            "Acquisition Period": [metrics.cohort.label],
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

def _download(frame: pd.DataFrame, name: str, key: str) -> None:
    """Export exactly the table shown -- values only, no formula hierarchy."""
    st.download_button(
        f"Download CSV ({len(frame):,} rows)",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=name,
        mime="text/csv",
        key=key,
        on_click=lambda: log_event("csv_export", file=name, rows=len(frame)),
    )


def _render_summary(metrics: CohortMetrics, age_month: int | None) -> None:
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
    _download(summary, "cohort_summary.csv", "dl_summary")

    if age_month is not None:
        st.markdown(f"**Selected month — Month {age_month}**")
        detail = month_summary(metrics, age_month)
        st.dataframe(
            detail,
            hide_index=True,
            width="stretch",
            column_config={
                "Monthly Contribution": st.column_config.NumberColumn(format="$%.2f"),
                "Cumulative Value": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
        _download(detail, f"month_{age_month}_summary.csv", "dl_month")


def _render_rows(metrics: CohortMetrics, metric_id: str, age_month: int | None) -> None:
    window = metrics.cohort.window
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
            f"Every user acquired {metrics.cohort.label}, with their orders and "
            f"gross value over their first {window} months. Users who never "
            f"ordered appear with zeros."
        )
        filename = f"underlying_users_{window}m.csv"
        money_columns = [f"gross_value_{window}m"]
    else:
        frame = order_rows(metrics, age_month)
        scope = f" in month {age_month}" if age_month is not None else ""
        caption = (
            f"Every order{scope} placed by these users within their first "
            f"{window} months. gross_value is revenue − cost."
        )
        filename = f"underlying_orders_{window}m.csv"
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
    _download(frame, filename, "dl_rows")


@st.dialog("View Underlying Data", width="large")
def render_underlying_data(metrics: CohortMetrics) -> None:
    nav: list[str] = st.session_state.metric_nav
    metric_id = nav[-1] if nav else PRIMARY_ID
    age_month = st.session_state.get("selected_month")

    st.markdown(f"### {METRICS[metric_id].name(metrics)}")
    scope = f" · Month {age_month} selected" if age_month is not None else ""
    st.caption(
        f"Users acquired {metrics.cohort.label} · first {metrics.cohort.window} "
        f"months{scope}"
    )

    summary_tab, rows_tab = st.tabs(["Summary", "Underlying rows"])
    with summary_tab:
        _render_summary(metrics, age_month)
    with rows_tab:
        _render_rows(metrics, metric_id, age_month)

    st.divider()
    back_col, close_col = st.columns([1, 1])

    if nav and back_col.button("← Back to Metric Details", key="underlying_back"):
        st.session_state.open_panel = "details"
        st.rerun()

    if close_col.button("Close", key="underlying_close"):
        st.session_state.open_panel = None
        st.rerun()
