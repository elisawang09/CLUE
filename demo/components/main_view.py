import streamlit as st
from .top_view import PRIMARY_METRIC, render_top_view
from .provenance_graph import render_provenance_graph
from .transformation_graph import render_transformation_graph
from data.metrics import (
    BaselineMetrics,
    decimal,
    failed_checks,
    load_baseline,
    md,
    money,
    node_values,
    percent,
)
from utils.graph_styles import legend_style_html, transformation_legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay


def _reference_caption(baseline: BaselineMetrics) -> str:
    """One line naming the acquisition group these numbers describe."""
    return (
        f"Historical baseline · {baseline.acquired_users:,} users acquired "
        f"{baseline.period_label}, each observed for their own first "
        f"{baseline.window} months."
    )


def _build_accumulation_values(baseline: BaselineMetrics) -> list[dict[str, object]]:
    """
    Value accumulated per acquired user by each month after acquisition.

    Months are counted from each user's own acquisition date, so month 6 is the
    end of every user's observation window and lands on the headline value.
    """
    last = baseline.window
    return [
        {
            "month": f"Month {month}",
            "value": round(value, 2),
            "is_last": month == last,
        }
        for month, value in zip(baseline.months, baseline.cumulative_value)
    ]


def _build_accumulation_vega_spec(baseline: BaselineMetrics) -> dict:
    """Vega-Lite spec for the accumulation line with its final point highlighted."""
    ceiling = max(baseline.cumulative_value or [0.0]) * 1.15 or 1.0
    return {
        "height": 200,
        "layer": [
            {
                "mark": {"type": "line", "color": "#2F3E7C", "strokeWidth": 4},
                "encoding": {
                    "x": {
                        "field": "month",
                        "type": "ordinal",
                        "sort": None,
                        "axis": {"title": None, "labelAngle": 0, "labelColor": "#7B7F87", "grid": False},
                    },
                    "y": {
                        "field": "value",
                        "type": "quantitative",
                        "scale": {"domain": [0, ceiling]},
                        "axis": {
                            "title": None,
                            "format": "$,.0f",
                            "tickCount": 6,
                            "labelColor": "#7B7F87",
                            "gridColor": "#E5E7EB",
                        },
                    },
                },
            },
            {
                "mark": {"type": "point", "filled": True, "size": 1800, "color": "#C9CDD3", "opacity": 0.75},
                "encoding": {
                    "x": {"field": "month", "type": "ordinal", "sort": None},
                    "y": {"field": "value", "type": "quantitative"},
                    "opacity": {"condition": {"test": "datum.is_last", "value": 0.75}, "value": 0},
                },
            },
            {
                "mark": {"type": "point", "filled": True, "size": 110, "color": "#111111"},
                "encoding": {
                    "x": {"field": "month", "type": "ordinal", "sort": None},
                    "y": {"field": "value", "type": "quantitative"},
                    "opacity": {"condition": {"test": "datum.is_last", "value": 1}, "value": 0},
                },
            },
        ],
        "config": {"view": {"stroke": None}},
    }


def _render_metric_overview(baseline: BaselineMetrics) -> None:
    """Render the main overview card with the value accumulation chart."""
    with st.container(border=True, height=350, key="card_main_overview"):
        st.subheader("Metric Overview")
        st.markdown(
            f"###### {PRIMARY_METRIC}: {md(money(baseline.customer_value))} per acquired user"
        )
        st.vega_lite_chart(
            _build_accumulation_values(baseline),
            _build_accumulation_vega_spec(baseline),
            use_container_width=True,
        )
        st.caption(_reference_caption(baseline))


def _render_ai_explanation(baseline: BaselineMetrics) -> None:
    """Render a concise bullet-style explanation for the selected metric."""
    with st.container(border=True, height=450, key="card_main_explanation"):
        st.subheader("AI-Generated Explanation")
        st.markdown(
            f"""
**{PRIMARY_METRIC}** shows the average value generated per acquired user during
the first 6 months after acquisition. It is calculated from three factors:
  - the percentage of acquired users who make at least one purchase within
    6 months — currently **{percent(baseline.conversion_rate)}**
  - the average number of orders placed by those purchasing customers —
    currently **{decimal(baseline.orders_per_purchasing_customer)}**
  - the average value generated per order — currently
    **{md(money(baseline.average_order_value))}**

Multiplying the three gives **{md(money(baseline.customer_value))}** per acquired user.
Every user acquired in the reference period counts toward that average, including
those who never placed an order.

The value shown here is calculated from the selected historical acquisition group:
users acquired {baseline.period_label}.
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
