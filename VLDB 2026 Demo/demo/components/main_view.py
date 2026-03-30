import streamlit as st
from .top_view import render_top_view

def render_main_view() -> None:
    # Inline row
    with st.container():
        render_top_view(button_text="Launch Metric Simulator", view_type="simulator")

    col1, col2 = st.columns([1.0, 3])

    with col1:
        search_metric = (st.session_state.search_query or "").strip().lower()

        with st.container(border=True, height=250, key="card_main_overview"):
            st.subheader("Metric Overview")
            if search_metric == "pltv":
                st.markdown("###### Predicted Liftetime Value (PLTV)")
                trend_values = [
                    {"date": "2025-11-23", "value": 21000},
                    {"date": "2025-11-24", "value": 22000},
                    {"date": "2025-11-25", "value": 27000},
                    {"date": "2025-11-25T12:00:00", "value": 25800},
                    {"date": "2025-11-26", "value": 29000},
                    {"date": "2025-11-27", "value": 32700},
                    {"date": "2025-11-27T08:00:00", "value": 32000},
                    {"date": "2025-11-28", "value": 37600},
                    {"date": "2025-11-28T10:00:00", "value": 34300},
                    {"date": "2025-11-28T18:00:00", "value": 40200},
                    {"date": "2025-11-29", "value": 38200},
                    {"date": "2025-11-29T10:00:00", "value": 47000},
                ]

                vega_spec = {
                    "height": 150,
                    "layer": [
                        {
                            "mark": {"type": "line", "color": "#2F3E7C", "strokeWidth": 4},
                            "encoding": {
                                "x": {
                                    "field": "date",
                                    "type": "temporal",
                                    "axis": {"title": None, "format": "%-d %b", "labelColor": "#7B7F87", "grid": False},
                                },
                                "y": {
                                    "field": "value",
                                    "type": "quantitative",
                                    "scale": {"domain": [20000, 50000]},
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

                st.vega_lite_chart(trend_values, vega_spec, use_container_width=True)

        with st.container(border=True, height=350, key="card_main_explanation"):
            st.subheader("AI-Generated Explanation")
            if search_metric == "pltv":
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

    with col2:
        with st.container(border=True, height=300, key="card_main_provenance"):
            st.subheader("Provenance of Metric:")
            if search_metric == "pltv":
                st.subheader("PLTV")
                st.write("Showing PLTV-specific lineage graphs.")

        with st.container(border=True, height=300, key="card_main_transformation"):
            st.subheader("Transformation View")
            if search_metric == "pltv":
                st.write("Showing PLTV-specific data quality issues.")
