import streamlit as st
from .top_view import render_top_view
from .provenance_graph import render_provenance_graph
from .transformation_graph import render_transformation_graph
from utils.graph_styles import legend_style_html, transformation_legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay

def _is_pltv_selected() -> bool:
    """Return whether the currently selected metric is PLTV."""
    selected = (st.session_state.search_query or "").strip().lower()
    return selected == "pltv"


def _build_pltv_trend_values() -> list[dict[str, int | str]]:
    """Create demo PLTV trend points used by the overview line chart."""
    return [
        {"date": "2025-04-30", "value": 44.7},
        {"date": "2025-05-31", "value": 46.8},
        {"date": "2025-06-30", "value": 57.4},
        {"date": "2025-07-31T12:00:00", "value": 54.9},
        {"date": "2025-08-31", "value": 61.7},
        {"date": "2025-09-30", "value": 69.6},
        {"date": "2025-10-31T08:00:00", "value": 68.1},
        {"date": "2025-11-30", "value": 80.0},
        {"date": "2025-12-31T10:00:00", "value": 73.0},
        {"date": "2026-01-31T18:00:00", "value": 85.5},
        {"date": "2026-02-28", "value": 81.3},
        {"date": "2026-03-31T10:00:00", "value": 100.0}
    ]


def _build_pltv_vega_spec() -> dict:
    """Build the Vega-Lite spec for a single PLTV trend line with highlighted last point."""
    return {
        "height": 200,
        "layer": [
            {
                "mark": {"type": "line", "color": "#2F3E7C", "strokeWidth": 4},
                "encoding": {
                    "x": {
                        "field": "date",
                        "type": "temporal",
                        "axis": {"title": None, "format": "%b %-y", "labelColor": "#7B7F87", "grid": False},
                    },
                    "y": {
                        "field": "value",
                        "type": "quantitative",
                        "scale": {"domain": [40, 120]},
                        "axis": {
                            "title": None,
                            "format": "$,.0f",
                            "tickCount": 7,
                            "labelColor": "#7B7F87",
                            "gridColor": "#E5E7EB",
                        },
                    },
                },
            },
            {
                "transform": [{"window": [{"op": "rank", "as": "r"}], "sort": [{"field": "date", "order": "descending"}]}],
                "mark": {"type": "point", "filled": True, "size": 1800, "color": "#C9CDD3", "opacity": 0.75},
                "encoding": {
                    "x": {"field": "date", "type": "temporal"},
                    "y": {"field": "value", "type": "quantitative"},
                    "opacity": {"condition": {"test": "datum.r == 1", "value": 0.75}, "value": 0},
                },
            },
            {
                "transform": [{"window": [{"op": "rank", "as": "r"}], "sort": [{"field": "date", "order": "descending"}]}],
                "mark": {"type": "point", "filled": True, "size": 110, "color": "#111111"},
                "encoding": {
                    "x": {"field": "date", "type": "temporal"},
                    "y": {"field": "value", "type": "quantitative"},
                    "opacity": {"condition": {"test": "datum.r == 1", "value": 1}, "value": 0},
                },
            },
        ],
        "config": {"view": {"stroke": None}},
    }


def _render_metric_overview() -> None:
    """Render the main overview card with the PLTV trend chart."""
    with st.container(border=True, height=350, key="card_main_overview"):
        st.subheader("Metric Overview")
        if not _is_pltv_selected():
            return

        st.markdown("###### Predicted Lifetime Value (PLTV)")
        st.vega_lite_chart(_build_pltv_trend_values(), _build_pltv_vega_spec(), use_container_width=True)


def _render_ai_explanation() -> None:
    """Render a concise bullet-style explanation for the selected metric."""
    with st.container(border=True, height=450, key="card_main_explanation"):
        st.subheader("AI-Generated Explanation")
        if not _is_pltv_selected():
            return

        st.markdown(
            """
Predicted Lifetime Value (PLTV) estimates how much revenue a typical customer is expected to generate over their lifetime.
It is calculated using three factors:
  - how likely a customer segment is to be active
  - how many orders active customers usually place
  - and the average value of each order.

For example, if more customers remain active, place orders more often, or spend more per order, the PLTV increases.
"""
        )


def _render_provenance_view() -> None:
    """Render the provenance panel for the currently selected metric."""
    active_node: str | None = st.session_state.get("selected_node")

    with st.container(border=True, height=400, key="card_main_provenance"):
        st.subheader("Provenance of Metric", help="Click a leaf metric to highlight its computation path from source tables.")
        if _is_pltv_selected():

            # ---------------------------------------------------------------------------
            # Legend
            # ---------------------------------------------------------------------------
            st.markdown(legend_style_html(), unsafe_allow_html=True)

            # ---------------------------------------------------------------------------
            # Provenance Graph
            # ---------------------------------------------------------------------------

            clicked = render_provenance_graph(highlighted_node=active_node)

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
        if _is_pltv_selected():
            # ---------------------------------------------------------------------------
            # Legend
            # ---------------------------------------------------------------------------
            st.markdown(transformation_legend_style_html(), unsafe_allow_html=True)

            render_transformation_graph(active_node)


def render_main_view() -> None:
    """Render the main dashboard view with overview, explanation, and lineage panels."""
    inject_tooltip_overlay()

    with st.container():
        render_top_view(button_text="🚀 Launch Metric Simulator", view_type="simulator")

    col1, col2 = st.columns([1.0, 3])

    with col1:
        _render_metric_overview()
        _render_ai_explanation()

    with col2:
        _render_provenance_view()
        _render_transformation_view()
