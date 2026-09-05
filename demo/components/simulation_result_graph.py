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

from data.graph_data import SimulationDelta, simulation_deltas
from utils.graph_builders import build_simulation_flow_elements

# ---------------------------------------------------------------------------
# Session-state cache
# ---------------------------------------------------------------------------

_SIM_GRAPH_KEY = "sim_graph_state"

# Cached flow states are kept per distinct scenario. Selecting scenarios is now
# the whole interaction, so the cache would otherwise grow a permanent entry
# for every set of assumptions a participant ever looked at -- including every
# step of a slider drag. Six is the size of the scenario list.
_MAX_CACHED_GRAPHS = 6
_ORDER_KEY = "sim_graph_order"


def _signature(deltas: dict[str, SimulationDelta]) -> str:
    """A stable id for one set of node deltas."""
    return str(hash(repr(sorted(deltas.items()))))


def _cached_state(signature: str, deltas: dict[str, SimulationDelta]):
    """Flow state for these deltas, building it once and evicting the oldest."""
    cache_key = f"{_SIM_GRAPH_KEY}_{signature}"
    order: list[str] = st.session_state.setdefault(_ORDER_KEY, [])

    if cache_key not in st.session_state:
        nodes, edges = build_simulation_flow_elements(deltas=deltas)
        st.session_state[cache_key] = StreamlitFlowState(nodes, edges)
        order.append(cache_key)
        while len(order) > _MAX_CACHED_GRAPHS:
            st.session_state.pop(order.pop(0), None)

    return st.session_state[cache_key]

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
        Optional override for node delta data.  When None, the scenario
        propagated from the historical baseline by graph_data is used.  Pass a
        custom dict to reflect dynamically computed simulation results.
    """
    effective_deltas = deltas if deltas is not None else simulation_deltas()
    signature = _signature(effective_deltas)
    state: StreamlitFlowState = _cached_state(signature, effective_deltas)

    # The component key carries the signature. A fixed key with a changing
    # state leaves the previously mounted graph on screen -- harmless when
    # simulating was a button press, but selecting scenarios is now the whole
    # interaction, so a stale graph would be the first thing anyone noticed.
    # transformation_graph.py keys per node for the same reason.
    streamlit_flow(
        key=f"simulation_result_{signature}",
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
