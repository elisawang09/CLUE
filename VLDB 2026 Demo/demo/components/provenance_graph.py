"""
provenance_graph.py
-------------------
Renders the provenance graph using streamlit-flow-component.

Interaction model
~~~~~~~~~~~~~~~~~
streamlit-flow-component does not expose a hover callback, so path
highlighting is driven by **node click** via `get_node_on_click=True`.
The component returns the clicked node's id directly into Python on each
rerun.
On the next rerun, `build_streamlit_flow_elements(highlighted_node=clicked)`
rebuilds the node/edge lists with highlight styles applied, and a fresh
StreamlitFlowState is passed to streamlit_flow() — the graph re-renders
with the highlighted path.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.state import StreamlitFlowState

from data.graph_data import LEAF_IDS, NODE_MAP
from utils.graph_utils import build_streamlit_flow_elements

# ---------------------------------------------------------------------------
# Session-state key
# ---------------------------------------------------------------------------

_SELECTED_KEY = "selected_node"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_provenance_graph(highlighted_node: Optional[str] = None) -> Optional[str]:
    """
    Render the provenance graph and return the id of the clicked node,
    or None if nothing was clicked this rerun.

    The caller (main_view.py) is responsible for persisting the returned value
    into session_state and passing it back as `highlighted_node` on the
    next call.
    """
    print(f"<Prov Graph> node id: {highlighted_node}")

    # Cache key for this graph build
    cache_key = f"prov_graph_{highlighted_node}"

    if cache_key not in st.session_state:
        nodes, edges = build_streamlit_flow_elements(highlighted_node=highlighted_node)
        st.session_state[cache_key] = StreamlitFlowState(nodes, edges)

    state = st.session_state[cache_key]

    result = streamlit_flow(
        key="provenance",
        state=state,
        height=400,
        fit_view=True,
        show_controls=False,
        show_minimap=False,
        allow_new_edges=False,
        animate_new_edges=False,
        get_node_on_click=True,
        get_edge_on_click=False,
        pan_on_drag=True,
        style={"background": "#F8FAFC"},
    )

    # streamlit_flow returns the full updated state; the clicked node id is
    # stored in state.selected_id when get_node_on_click=True.
    if result and hasattr(result, "selected_id") and result.selected_id:
        clicked_id = result.selected_id
        # Only leaf nodes trigger a path highlight
        if clicked_id in LEAF_IDS:
            return clicked_id
        # Clicking the same leaf again deselects
    return None