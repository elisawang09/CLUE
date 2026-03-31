"""
graph_builders.py
-----------------
Public builders that assemble StreamlitFlowNode / StreamlitFlowEdge lists
for each of the three graph types:

  - build_streamlit_flow_elements()     → provenance graph
  - build_simulation_flow_elements()    → simulation result graph
  - build_transformation_flow_elements() → data transformation graph

All traversal logic is delegated to graph_utils; all styling to graph_styles.
"""

from __future__ import annotations

from typing import Optional

from data.graph_data import (
    EDGES,
    LEAF_IDS,
    NODES,
    SIMULATION_DELTAS,
    TRANSFORMATION_FLOWS,
    SimulationDelta,
)
from utils.graph_utils import ancestors_of, path_edges
from utils.graph_styles import (
    COLORS,
    node_label,
    node_label_sim,
    node_style,
    node_style_sim,
    operator_svg_icon,
    transformation_node_html,
    transformation_node_style,
)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _is_leaf(node_id: str) -> bool:
    """Return True if node_id has no outgoing edges (i.e. is a leaf)."""
    return node_id in LEAF_IDS


# ---------------------------------------------------------------------------
# Provenance graph builder
# ---------------------------------------------------------------------------

def build_streamlit_flow_elements(
    highlighted_node: Optional[str] = None,
) -> tuple[list, list]:
    """
    Build (nodes, edges) for the provenance graph.

    Parameters
    ----------
    highlighted_node :
        Leaf node id whose root-to-leaf path should be highlighted.
        Pass None for no highlighting.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    X_SCALE, Y_SCALE   = 260, 85
    X_OFFSET, Y_OFFSET = 10,  60

    h_nodes: set[str]              = set()
    h_edges: set[tuple[str, str]]  = set()
    if highlighted_node:
        h_nodes = ancestors_of(highlighted_node)
        h_edges = path_edges(highlighted_node)

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(X_OFFSET + node.x * X_SCALE, Y_OFFSET + node.y * Y_SCALE),
            data={"label": node_label(node, highlighted=(node.id in h_nodes))},
            node_type="default",
            source_position="right",
            target_position="left",
            draggable=False,
            style=node_style(node, highlighted=(node.id in h_nodes)),
        )
        for node in NODES
    ]

    sf_edges = [
        StreamlitFlowEdge(
            id=f"e{i}",
            source=edge.source,
            target=edge.target,
            edge_type="smoothstep",
            animated=(edge.source, edge.target) in h_edges,
            style={
                "stroke":      COLORS["edge_hl"] if (edge.source, edge.target) in h_edges else COLORS["edge_normal"],
                "strokeWidth": 2.5               if (edge.source, edge.target) in h_edges else 1.5,
            },
            marker_end={
                "type":  "arrowclosed",
                "color": COLORS["edge_hl"] if (edge.source, edge.target) in h_edges else COLORS["edge_normal"],
            },
        )
        for i, edge in enumerate(EDGES)
    ]

    return sf_nodes, sf_edges

# ---------------------------------------------------------------------------
# Simulation result graph builder
# ---------------------------------------------------------------------------

def build_simulation_flow_elements(
    deltas: Optional[dict[str, SimulationDelta]] = None,
) -> tuple[list, list]:
    """
    Build (nodes, edges) for the simulation result graph.

    Every provenance node is included; nodes with a matching SimulationDelta
    get a delta badge appended to their label.

    Parameters
    ----------
    deltas :
        Mapping of node_id → SimulationDelta.  Defaults to
        SIMULATION_DELTAS from graph_data when None.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    effective_deltas = SIMULATION_DELTAS if deltas is None else deltas

    X_SCALE, Y_SCALE   = 270, 100
    X_OFFSET, Y_OFFSET = 10,  70

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(X_OFFSET + node.x * X_SCALE, Y_OFFSET + node.y * Y_SCALE),
            data={"label": node_label_sim(
                node,
                delta=effective_deltas.get(node.id)
            )},
            node_type="default",
            source_position="right",
            target_position="left",
            draggable=False,
            style=node_style_sim(node),
        )
        for node in NODES
    ]

    sf_edges = [
        StreamlitFlowEdge(
            id=f"se{i}",
            source=edge.source,
            target=edge.target,
            edge_type="smoothstep",
            animated=False,
            style={"stroke": COLORS["edge_normal"], "strokeWidth": 1.5},
            marker_start={"type": "arrowclosed", "color": COLORS["edge_normal"]},
            # marker_end={"type": "arrowclosed", "color": COLORS["edge_normal"]},
        )
        for i, edge in enumerate(EDGES)
    ]

    return sf_nodes, sf_edges


# ---------------------------------------------------------------------------
# Transformation flow graph builder
# ---------------------------------------------------------------------------

def build_transformation_flow_elements(
    leaf_node_id: Optional[str] = None,
) -> tuple[list, list]:
    """
    Build (nodes, edges) for the data transformation flow graph.

    Parameters
    ----------
    leaf_node_id :
        The leaf node ID whose transformation pipeline should be rendered.
        Returns empty lists when None or not found in TRANSFORMATION_FLOWS.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    if not leaf_node_id or leaf_node_id not in TRANSFORMATION_FLOWS:
        return [], []

    trans_nodes, trans_edges = TRANSFORMATION_FLOWS[leaf_node_id]

    STATIC_URL = "http://localhost:8502/app/static"
    TX_SCALE, TY_SCALE   = 280, 140
    TX_OFFSET, TY_OFFSET = 20,  40

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(TX_OFFSET + node.x * TX_SCALE, TY_OFFSET + node.y * TY_SCALE),
            data={"content": transformation_node_html(node, STATIC_URL)},
            node_type="default",
            source_position="right",
            target_position="left",
            draggable=False,
            style=transformation_node_style(node),
        )
        for node in trans_nodes
    ]

    sf_edges = [
        StreamlitFlowEdge(
            id=f"te{i}",
            source=edge.source,
            target=edge.target,
            edge_type="smoothstep",
            style={"stroke": "#94A3B8",
                    "strokeWidth": 1.5,
                    "fontSize": "13px",
                    "cursor": "default"},
            marker_end={"type": "arrowclosed", "color": "#94A3B8"},
            label=edge.label or None,
        )
        for i, edge in enumerate(trans_edges)
    ]

    return sf_nodes, sf_edges
