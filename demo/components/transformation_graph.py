"""
transformation_graph.py
-----------------------
Renders the data transformation flow for a selected leaf node.

When a user clicks on a leaf node in the provenance graph, this component
displays a detailed transformation flow showing how that metric is computed
from raw source tables through various filters, joins, and aggregations.

Each node displays:
  - A label (e.g., "raw_orders", "Total Gross Order Value")
  - Color-coded by transformation type (source table, filter, join, etc.)
  - Optional icons

Edges show transformation operations and their types.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.state import StreamlitFlowState
from utils.graph_builders import build_transformation_flow_elements

def render_transformation_graph(leaf_node_id: str):
    """
    Render the transformation flow graph for a given leaf node.
    Uses session state caching to prevent infinite re-renders.
    """

    print(f"<Trans> Clicked node id: {leaf_node_id}")
    # Cache nodes/edges in session state to prevent re-building
    cache_key = f"trans_graph_{leaf_node_id}"

    if cache_key not in st.session_state:
        nodes, edges = build_transformation_flow_elements(leaf_node_id)

        if not nodes:
            st.info("No transformation data available for this node.")
            return

        st.session_state[cache_key] = StreamlitFlowState(nodes, edges)

    flow_state = st.session_state[cache_key]

    # Render the flow graph with fixed config
    streamlit_flow(
        f"flow_{leaf_node_id}",  # Unique key per node to prevent state pollution
        state=flow_state,
        height=300,
        style={"background": "#F8FAFC"},
        fit_view=True,
        show_controls=False,
        show_minimap=False,
        allow_zoom=True,
        get_node_on_click=False,
        pan_on_drag=True
    )
