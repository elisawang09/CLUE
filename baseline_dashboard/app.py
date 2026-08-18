"""
Customer Value Dashboard -- baseline (control) condition for the CLUE study.

A conventional BI dashboard: filters, KPI cards, two charts, and the ordinary
inspection affordances (metric details, calculation expression, view underlying
data, CSV export). Deliberately *not* a lineage or modeling tool -- there is no
provenance graph, no dependency tree, and no simulator here.

Run from this directory:
    python -m datasource.build      # once, to build the modeled data source
    streamlit run app.py
"""

import streamlit as st

from components.charts import (
    CHART_PANEL_HEIGHT,
    render_contribution_chart,
    render_cumulative_chart,
)
from components.filters import render_filters
from components.header import render_header
from components.kpi_cards import render_kpi_cards
from components.metric_details import render_metric_details
from components.styles import highlight_selected_card, inject_styles
from components.underlying_data import render_underlying_data
from datasource.loader import available_months, load_age_facts, load_customers
from datasource.schema import DataSourceError
from metrics.checks import run_checks
from metrics.compute import compute
from study.events import log_event, log_if_changed, log_session_start
from study.session import resolve_session


def _init_state() -> None:
    defaults = {
        "selected_metric": None,   # which KPI card is outlined
        "metric_nav": [],          # drill path through metric definitions
        "selected_month": None,    # age month clicked on a chart
        "open_panel": None,        # "details" | "underlying" | None
        "underlying_tab": "summary",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _open_panel(metric_id: str, action: str, session) -> None:
    """Open a panel from a card menu, and record that it happened."""
    st.session_state.selected_metric = metric_id
    st.session_state.metric_nav = [metric_id]
    st.session_state.open_panel = action
    log_event(f"open_{action}", session, metric=metric_id, source="card_menu")


def _report_checks(metrics) -> None:
    """
    Surface a broken metric loudly.

    If the headline ever disagreed with its own components, the study task would
    be measuring a bug rather than a participant, so this is worth a banner
    rather than a silent log line.
    """
    failed = [check for check in run_checks(metrics) if not check.passed]
    if failed:
        st.error(
            "Metric consistency check failed — these numbers should not be "
            "used:\n\n"
            + "\n".join(f"- **{c.name}** — {c.detail}" for c in failed)
        )


def main() -> None:
    st.set_page_config(
        page_title="Customer Value Dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    _init_state()

    # Which study condition this browser session is in. Resolved once from the
    # link's token and pinned, so it cannot change mid-task.
    session = resolve_session()
    log_session_start(session)

    try:
        customers = load_customers()
        age_facts = load_age_facts()
        months = available_months()
    except DataSourceError as error:
        st.error(str(error))
        st.stop()
        return

    render_header()
    cohort = render_filters(months)
    metrics = compute(customers, age_facts, cohort)
    _report_checks(metrics)

    log_if_changed("filter_period", "_logged_period", cohort.label, session)
    log_if_changed("filter_window", "_logged_window", cohort.window, session)

    highlight_selected_card(st.session_state.selected_metric)
    metric_id, action = render_kpi_cards(
        metrics, st.session_state.selected_metric, session
    )
    if metric_id and action:
        _open_panel(metric_id, action, session)

    # Fixed height on both so the two panels stay level even if one subtitle
    # wraps to a different number of lines than the other.
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True, height=CHART_PANEL_HEIGHT,
                            key="chart_left"):
        picked_left = render_cumulative_chart(metrics)
    with right, st.container(border=True, height=CHART_PANEL_HEIGHT,
                             key="chart_right"):
        picked_right = render_contribution_chart(metrics)

    picked = picked_left if picked_left is not None else picked_right
    if picked != st.session_state.selected_month:
        st.session_state.selected_month = picked
        if picked is not None:
            log_event("chart_select", session, age_month=picked)

    if st.session_state.open_panel == "details":
        render_metric_details(metrics)
    elif st.session_state.open_panel == "underlying":
        render_underlying_data(metrics)

    st.caption(
        f"Customer Analytics Model · {metrics.acquired_users:,} users acquired "
        f"{cohort.label}, each observed for their own first {cohort.window} months."
    )


main()
