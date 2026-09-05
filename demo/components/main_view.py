import streamlit as st
from .top_view import PRIMARY_METRIC, render_top_view
from .provenance_graph import render_provenance_graph
from .transformation_graph import render_transformation_graph
from data.metrics import (
    BaselineMetrics,
    failed_checks,
    load_baseline,
    md,
    money,
    node_values,
)
from utils.graph_styles import legend_style_html, transformation_legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay


def _build_chart_values(baseline: BaselineMetrics) -> list[dict[str, object]]:
    """
    One row per acquisition month in the reference period.

    This is the chart the participant just left on the baseline dashboard, so
    they arrive in CLUE looking at the same shape they clicked from -- with the
    month CLUE explains picked out of it.
    """
    return [
        {
            "month": point.month_label,
            "value": round(point.customer_value, 2),
            "is_focus": point.is_focus,
        }
        for point in baseline.by_month
    ]


def _build_chart_vega_spec(baseline: BaselineMetrics) -> dict:
    """
    Vega-Lite spec for the acquisition-month columns.

    The explained month is drawn in CLUE's accent and every other month is
    muted: the emphasis is what ties the headline above to a bar below. Only
    that bar is labelled, because it is the one number the card is about.
    """
    values = [point.customer_value for point in baseline.by_month] or [0.0]
    ceiling = max(values) * 1.2 or 1.0
    focus_colour = "#2F3E7C"
    muted_colour = "#C9CDD3"

    x_encoding = {
        "field": "month",
        "type": "ordinal",
        "sort": None,
        "axis": {
            "title": "User Acquisition Month",
            "labelAngle": 0 if len(baseline.by_month) <= 8 else -45,
            "labelColor": "#7B7F87",
            "titleColor": "#7B7F87",
            "grid": False,
        },
    }
    y_encoding = {
        "field": "value",
        "type": "quantitative",
        "scale": {"domain": [0, ceiling]},
        "axis": {
            "title": None,
            "format": "$,.0f",
            "tickCount": 5,
            "labelColor": "#7B7F87",
            "gridColor": "#E5E7EB",
        },
    }

    return {
        "height": 200,
        "layer": [
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusTopLeft": 4,
                    "cornerRadiusTopRight": 4,
                },
                "encoding": {
                    "x": x_encoding,
                    "y": y_encoding,
                    "color": {
                        "condition": {
                            "test": "datum.is_focus",
                            "value": focus_colour,
                        },
                        "value": muted_colour,
                    },
                    "tooltip": [
                        {"field": "month", "type": "ordinal",
                         "title": "User Acquisition Month"},
                        {"field": "value", "type": "quantitative",
                         "title": PRIMARY_METRIC, "format": "$,.2f"},
                    ],
                },
            },
            {
                "mark": {
                    "type": "text",
                    "dy": -8,
                    "fontSize": 12,
                    "fontWeight": "bold",
                    "color": "#111111",
                },
                "encoding": {
                    "x": x_encoding,
                    "y": y_encoding,
                    "text": {
                        "field": "value",
                        "type": "quantitative",
                        "format": "$,.2f",
                    },
                    "opacity": {
                        "condition": {"test": "datum.is_focus", "value": 1},
                        "value": 0,
                    },
                },
            },
        ],
        "config": {"view": {"stroke": None}},
    }


def _render_metric_overview(baseline: BaselineMetrics) -> None:
    """Render the main overview card with the acquisition-month chart."""
    with st.container(border=True, height=350, key="card_main_overview"):
        st.subheader("Metric Overview")
        st.markdown(
            f"###### {PRIMARY_METRIC}: {md(money(baseline.customer_value))} per acquired user"
        )
        st.vega_lite_chart(
            _build_chart_values(baseline),
            _build_chart_vega_spec(baseline),
            use_container_width=True,
        )


def _render_ai_explanation(baseline: BaselineMetrics) -> None:
    """
    Say what the metric means, not what it currently is.

    The figures are already on the card above, in the provenance graph, and on
    the dashboard this hands over from. Repeating them here made the panel long
    enough that the explanation itself got lost, and gave three places for the
    same number to disagree.
    """
    with st.container(border=True, height=450, key="card_main_explanation"):
        st.subheader("AI-Generated Explanation")
        st.markdown(
            f"""
**{PRIMARY_METRIC}** is the average value a newly acquired user generates in
their first {baseline.window_days} days. Three things decide it:

- **Purchase conversion** — how many of the acquired users buy at all inside
  that window
- **Order frequency** — how often those customers come back
- **Average order value** — what each order is worth once its costs are taken out

The three multiply together to give the headline. Every acquired user counts
toward the average, including those who never order — that is what makes it a
value *per acquired user* rather than per customer.

The figure describes users acquired in **{baseline.cohort_label}**, the most
recent month in the reference period. The chart above places that month among
its neighbours.
"""
        )


def _render_provenance_view(baseline: BaselineMetrics) -> None:
    """Render the provenance panel for the currently selected metric."""
    active_node: str | None = st.session_state.get("selected_node")

    with st.container(border=True, height=400, key="card_main_provenance"):
        st.subheader("Provenance of Metric", help="Click a leaf metric to highlight its computation path from source tables.")

        # ---------------------------------------------------------------------------
        # Legend
        # ---------------------------------------------------------------------------
        st.markdown(legend_style_html(), unsafe_allow_html=True)

        # ---------------------------------------------------------------------------
        # Provenance Graph
        # ---------------------------------------------------------------------------

        clicked = render_provenance_graph(
            highlighted_node=active_node, values=node_values(baseline)
        )

        if clicked:
            print(f"Clicked node id: {active_node}, state before toggle: {st.session_state.get('selected_node')}")

            if st.session_state.get('selected_node') != clicked:
                st.session_state["selected_node"] = clicked
                _render_transformation_view()


def _render_transformation_view() -> None:
    """Render the transformation panel for the currently selected metric."""
    active_node: str | None = st.session_state.get("selected_node")

    with st.container(border=True, height=400, key="card_main_transformation"):
        st.subheader("Transformation View", help="Shows how the selected node is computed from raw source tables.")

        # ---------------------------------------------------------------------------
        # Legend
        # ---------------------------------------------------------------------------
        st.markdown(transformation_legend_style_html(), unsafe_allow_html=True)

        render_transformation_graph(active_node)


def _report_checks(baseline: BaselineMetrics) -> None:
    """
    Surface a broken metric loudly.

    If the headline ever disagreed with its own components, a study task would
    be measuring a bug rather than a participant, so this is worth a banner
    rather than a silent log line.
    """
    failed = failed_checks(baseline)
    if failed:
        st.error(
            "Metric consistency check failed — these numbers should not be "
            "used:\n\n"
            + "\n".join(f"- **{check.name}** — {check.detail}" for check in failed)
        )
    if baseline.is_fallback:
        st.caption(
            "Modeled data source not found — showing the reference example "
            "figures. Build it with `python -m datasource.build` from "
            "`baseline_dashboard/`."
        )


def render_main_view() -> None:
    """Render the main dashboard view with overview, explanation, and lineage panels."""
    inject_tooltip_overlay()

    baseline = load_baseline()

    with st.container():
        render_top_view(button_text="🚀 Launch Metric Simulator", view_type="simulator")

    _report_checks(baseline)

    col1, col2 = st.columns([1.0, 3])

    with col1:
        _render_metric_overview(baseline)
        _render_ai_explanation(baseline)

    with col2:
        _render_provenance_view(baseline)
        _render_transformation_view()
