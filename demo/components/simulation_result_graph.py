"""
simulation_result_graph.py
--------------------------
Renders the simulation result graph using streamlit-flow-component.

Reuses all provenance graph components (node styles, edge styles, operator
diamonds, metric/ratio pills) and layers SimulationDelta annotations onto
each node to show how values have changed relative to the baseline.

Public API
~~~~~~~~~~
    render_simulation_graph(deltas=None) -> None
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.state import StreamlitFlowState

from data.graph_data import SimulationDelta, SIMULATION_DELTAS
from utils.graph_builders import build_simulation_flow_elements

# ---------------------------------------------------------------------------
# Session-state cache key
# ---------------------------------------------------------------------------

_SIM_GRAPH_KEY = "sim_graph_state"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_simulation_graph(
    deltas: Optional[dict[str, SimulationDelta]] = None,
) -> None:
    """
    Render the simulation result graph inside the current Streamlit container.

    Parameters
    ----------
    deltas :
        Optional override for node delta data.  When None, the default
        SIMULATION_DELTAS defined in graph_data.py are used.  Pass a
        custom dict to reflect dynamically computed simulation results.
    """
    effective_deltas = deltas if deltas is not None else SIMULATION_DELTAS

    if deltas is None:
        cache_key = _SIM_GRAPH_KEY
    else:
        cache_key = f"{_SIM_GRAPH_KEY}_{hash(repr(sorted(deltas.items())))}"

    if cache_key not in st.session_state:
        nodes, edges = build_simulation_flow_elements(deltas=effective_deltas)
        st.session_state[cache_key] = StreamlitFlowState(nodes, edges)

    state: StreamlitFlowState = st.session_state[cache_key]

    streamlit_flow(
        key="simulation_result",
        state=state,
        height=460,
        fit_view=True,
        show_controls=False,
        show_minimap=False,
        allow_new_edges=False,
        animate_new_edges=False,
        get_node_on_click=False,
        get_edge_on_click=False,
        pan_on_drag=True,
        style={"background": "#F8FAFC"},
    )
