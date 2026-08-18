"""
metric_details.py
-----------------
The Metric Details / View Calculation panel.

Shows one metric definition at a time. Components in the calculation are
clickable, so someone can step from the headline down to `gross_value =
revenue - cost` one hop at a time, with a breadcrumb back out. It deliberately
never draws the whole dependency tree -- this is a conventional BI dashboard,
and reading a definition is supposed to feel like opening a calculated field,
not like opening a lineage tool.

Each component row carries its current value alongside its name, because the
task this panel supports is checking by hand that the parts really do multiply
out to the headline.
"""

import streamlit as st

from components.styles import TEXT_MUTED
from metrics.compute import CohortMetrics
from metrics.registry import METRICS, Token, formatted_value
from study.events import log_event


def _label(text: str) -> None:
    st.markdown(f'<p class="bd-panel-label">{text}</p>', unsafe_allow_html=True)


def _breadcrumb(nav: list[str], metrics: CohortMetrics) -> None:
    if len(nav) < 2:
        return
    trail = " › ".join(METRICS[metric_id].name(metrics) for metric_id in nav)
    st.markdown(f'<p class="bd-breadcrumb">{trail}</p>', unsafe_allow_html=True)


def _render_component_rows(tokens: list[Token], metrics: CohortMetrics) -> str | None:
    """
    Lay the calculation out as one row per referenced component.

    Returns a metric id if the participant drilled into one.
    """
    drilled: str | None = None

    for token in tokens:
        if token.ref is None:
            # An operator or connective between components.
            st.markdown(
                f'<div style="text-align:center;color:{TEXT_MUTED};'
                f'font-size:1.05rem;margin:-0.2rem 0 -0.2rem 0;">{token.text}</div>',
                unsafe_allow_html=True,
            )
            continue

        name_col, value_col, open_col = st.columns([3.2, 1.2, 1.1])
        name_col.markdown(
            f'<div class="bd-panel-text" style="padding-top:0.35rem;">'
            f"{token.text}</div>",
            unsafe_allow_html=True,
        )
        value_col.markdown(
            f'<div class="bd-panel-text" style="padding-top:0.35rem;text-align:right;'
            f'font-weight:700;">{formatted_value(token.ref, metrics)}</div>',
            unsafe_allow_html=True,
        )
        if open_col.button(
            "Open →", key=f"drill_{token.ref}", type="tertiary",
            help=f"View the calculation behind {token.text}",
        ):
            drilled = token.ref

    return drilled


def _render_body(metric_id: str, metrics: CohortMetrics) -> str | None:
    metric = METRICS[metric_id]
    tokens = metric.expression(metrics)

    st.markdown(f"### {metric.name(metrics)}")

    value = metric.value(metrics)
    if value is not None:
        unit = f' <span class="bd-kpi-unit">{metric.unit}</span>' if metric.unit else ""
        _label("Value")
        st.markdown(
            f'<div class="bd-panel-value">{formatted_value(metric_id, metrics)}'
            f"{unit}</div>",
            unsafe_allow_html=True,
        )

    _label("Description")
    st.markdown(
        f'<div class="bd-panel-text">{metric.description(metrics)}</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        _label("Reference acquisition period")
        st.markdown(
            f'<div class="bd-panel-text">{metrics.cohort.label}</div>',
            unsafe_allow_html=True,
        )
    with right:
        _label("Observation window")
        st.markdown(
            f'<div class="bd-panel-text">First {metrics.cohort.window} months '
            f"after each user's acquisition</div>",
            unsafe_allow_html=True,
        )

    _label("Calculation")
    drilled: str | None = None
    if any(token.ref for token in tokens):
        drilled = _render_component_rows(tokens, metrics)
    else:
        expression = " ".join(token.text for token in tokens)
        st.markdown(
            f'<div class="bd-expression">{expression}</div>', unsafe_allow_html=True
        )

    notes = metric.notes(metrics)
    if notes:
        st.caption(notes)

    _label("Data source")
    st.markdown(f'<div class="bd-source">{metric.source}</div>', unsafe_allow_html=True)

    return drilled


@st.dialog("Metric Details", width="large")
def render_metric_details(metrics: CohortMetrics) -> None:
    nav: list[str] = st.session_state.metric_nav
    if not nav:
        st.session_state.open_panel = None
        return

    _breadcrumb(nav, metrics)
    drilled = _render_body(nav[-1], metrics)

    if drilled:
        st.session_state.metric_nav = nav + [drilled]
        log_event("metric_drill", metric=drilled, depth=len(nav) + 1, came_from=nav[-1])
        st.rerun()

    st.divider()
    back_col, underlying_col, close_col = st.columns([1, 1.5, 1])

    if len(nav) > 1 and back_col.button("← Back", key="details_back"):
        st.session_state.metric_nav = nav[:-1]
        st.rerun()

    if underlying_col.button(
        "View Underlying Data", key="details_underlying", type="primary"
    ):
        st.session_state.open_panel = "underlying"
        st.session_state.underlying_tab = "summary"
        log_event("open_underlying", metric=nav[-1], source="metric_details")
        st.rerun()

    if close_col.button("Close", key="details_close"):
        st.session_state.open_panel = None
        st.session_state.metric_nav = []
        st.rerun()
