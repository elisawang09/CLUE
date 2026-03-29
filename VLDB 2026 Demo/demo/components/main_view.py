import streamlit as st
from .top_view import render_top_view

def render_main_view() -> None:
    # Inline row
    with st.container():
        render_top_view(button_text="Launch Metric Simulator", view_type="simulator")

    col1, col2 = st.columns([1.0, 3])

    with col1:
        search_metric = (st.session_state.search_query or "").strip().lower()

        with st.container(border=True, height=300):
            st.subheader("Metric Overview")
            if search_metric == "pltv":
                st.write("Showing PLTV-specific controls and summary.")
                st.metric("Current PLTV", "$1,240")

        with st.container(border=True, height=300):
            st.subheader("AI-Generated Explanation")
            if search_metric == "pltv":
                st.write(
                    "Predicted Lifetime Value (PLTV) estimates how much revenue a typical customer is expected to generate over their lifetime. "
                    "It is calculated using three factors: how likely a customer segment is to be active, how many orders active customers usually place, "
                    "and the average value of each order. For example, if more customers remain active, place orders more often, or spend more per order, the PLTV increases."
                )

    with col2:
        with st.container(border=True, height=300):
            st.subheader("Provenance of Metric:")
            if search_metric == "pltv":
                st.subheader("PLTV")
                st.write("Showing PLTV-specific lineage graphs.")

        with st.container(border=True, height=300):
            if search_metric == "pltv":
                st.subheader("Transformation")
                st.write("Showing PLTV-specific data quality issues.")
