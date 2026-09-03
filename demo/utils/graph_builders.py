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
    TRANSFORMATION_FLOWS,
    SimulationDelta,
    simulation_deltas,
)
from utils.graph_utils import ancestors_of, path_edges
from utils.graph_styles import (
    COLORS,
    STATIC_URL,
    TRANSFORMATION_NODE_HEIGHT,
    estimated_node_width,
    node_label,
    node_label_sim,
    node_style,
    node_style_sim,
    operator_svg_icon,
    transformation_node_html,
    transformation_node_style,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_leaf(node_id: str) -> bool:
    """Return True if node_id has no outgoing edges (i.e. is a leaf)."""
    return node_id in LEAF_IDS


TRANSFORMATION_EDGE_COLOR = "#94A3B8"


def _badge_text(delta: Optional[SimulationDelta]) -> Optional[str]:
    """Plain text of a delta badge, for width estimation only."""
    if delta is None:
        return None
    return f"{delta.delta_value} ({delta.label_prefix} {delta.prev_value})"


def _column_layout(
    nodes,
    x_offset: float,
    x_gap: float,
    widths: Optional[dict[str, float]] = None,
    gaps: Optional[dict[float, float]] = None,
) -> tuple[dict[float, float], dict[float, float]]:
    """
    Left edge and width in pixels for each logical column.

    Every node in a column starts at the same x, which is what keeps the
    operator diamonds vertically aligned. A column starts `x_gap` past the
    right edge of the widest node in the column before it, so the shortest
    edge on that boundary is `x_gap` long however wide the nodes get.

    `gaps` widens individual boundaries past `x_gap` -- the transformation
    graph uses it to leave room for the operation chip sitting on the edge.
    """
    node_widths = widths or {}
    column_gaps = gaps or {}

    columns: dict[float, list] = {}
    for node in nodes:
        columns.setdefault(node.x, []).append(node)

    positions: dict[float, float] = {}
    column_widths: dict[float, float] = {}
    x = x_offset
    for column in sorted(columns):
        positions[column] = x
        column_widths[column] = max(
            node_widths[node.id] if node.id in node_widths
            else estimated_node_width(node)
            for node in columns[column]
        )
        x += column_widths[column] + max(x_gap, column_gaps.get(column, 0))
    return positions, column_widths


# ---------------------------------------------------------------------------
# Provenance graph builder
# ---------------------------------------------------------------------------

def build_streamlit_flow_elements(
    highlighted_node: Optional[str] = None,
    values: Optional[dict[str, str]] = None,
) -> tuple[list, list]:
    """
    Build (nodes, edges) for the provenance graph.

    Parameters
    ----------
    highlighted_node :
        Leaf node id whose root-to-leaf path should be highlighted.
        Pass None for no highlighting.
    values :
        Formatted value per node id, shown in each node's hover tooltip.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    Y_SCALE            = 85
    X_OFFSET, Y_OFFSET = 10, 60
    X_GAP              = 45   # shortest edge between two columns

    node_values = values or {}
    column_x, _ = _column_layout(NODES, X_OFFSET, X_GAP)

    h_nodes: set[str]              = set()
    h_edges: set[tuple[str, str]]  = set()
    if highlighted_node:
        h_nodes = ancestors_of(highlighted_node)
        h_edges = path_edges(highlighted_node)

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(column_x[node.x], Y_OFFSET + node.y * Y_SCALE),
            data={"label": node_label(
                node,
                highlighted=(node.id in h_nodes),
                value=node_values.get(node.id),
            )},
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
                "cursor":      "none"
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
        Mapping of node_id → SimulationDelta.  Defaults to the scenario
        propagated from the historical baseline by graph_data when None.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    effective_deltas = simulation_deltas() if deltas is None else deltas

    Y_SCALE            = 100
    X_OFFSET, Y_OFFSET = 10, 70
    X_GAP              = 45   # shortest edge between two columns

    # A node here is as wide as its delta badge when that runs longer than the
    # metric name, so the badge is what decides where the next column starts.
    widths = {
        node.id: estimated_node_width(node, _badge_text(effective_deltas.get(node.id)))
        for node in NODES
    }
    column_x, _ = _column_layout(NODES, X_OFFSET, X_GAP, widths=widths)

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(column_x[node.x], Y_OFFSET + node.y * Y_SCALE),
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

    TY_SCALE             = 140
    TX_OFFSET, TY_OFFSET = 20, 40
    TX_GAP               = 45   # shortest edge between two columns

    # Transformation labels are table and column names, which run long.
    widths = {
        node.id: max(len(node.label) * 8.5 + 24, 130) for node in trans_nodes
    }

    # Every operation is drawn in the boundary immediately before its target
    # column (see the waypoint routing below), so that is the boundary that
    # has to be wide enough to hold the chip.
    node_column = {node.id: node.x for node in trans_nodes}
    chip_gaps: dict[float, float] = {}
    for edge in trans_edges:
        column = node_column[edge.target] - 1
        chip = len(edge.label or "") * 7.6 + 40
        chip_gaps[column] = max(chip_gaps.get(column, 0.0), chip)

    column_x, column_width = _column_layout(
        trans_nodes, TX_OFFSET, TX_GAP, widths=widths, gaps=chip_gaps
    )

    def _node_style(node) -> dict:
        # Every node in a column is given the column's width, so nodes in the
        # same column share a right edge and the steps read as a grid.
        style = transformation_node_style(node)
        style["width"] = f"{column_width[node.x]:.0f}px"
        return style

    def _row_y(node) -> float:
        return TY_OFFSET + node.y * TY_SCALE

    sf_nodes = [
        StreamlitFlowNode(
            id=node.id,
            pos=(column_x[node.x], _row_y(node)),
            data={"label": transformation_node_html(node, STATIC_URL)},
            node_type="default",
            source_position="right",
            target_position="left",
            draggable=False,
            style=_node_style(node),
        )
        for node in trans_nodes
    ]

    # A smoothstep edge always turns at the midpoint between its two nodes,
    # and the component gives no way to move that. An edge spanning several
    # columns would therefore turn far to the left of the short edge it joins
    # with. Routing it through a waypoint splits it into a horizontal run plus
    # a final segment identical in geometry to the short one -- so both turn,
    # and carry their chip, at the same x.
    #
    # The waypoint is a hairline sitting on the *right edge* of the column
    # before the target: its two handles are effectively the same point, so
    # the line stays near-continuous rather than jumping a node-sized gap, and
    # it is as tall as a real node so the run stays level with its source row.
    node_by_id = {node.id: node for node in trans_nodes}
    waypoints: list = []

    def _waypoint(edge) -> Optional[str]:
        source, target = node_by_id[edge.source], node_by_id[edge.target]
        turn_column = target.x - 1
        if source.x >= turn_column or turn_column not in column_x:
            return None

        waypoint_id = f"wp_{edge.source}_{edge.target}"
        right_edge = column_x[turn_column] + column_width[turn_column]
        waypoints.append(
            StreamlitFlowNode(
                id=waypoint_id,
                pos=(right_edge - 1, _row_y(source)),
                data={"label": ""},
                node_type="default",
                source_position="right",
                target_position="left",
                draggable=False,
                selectable=False,
                style={
                    "width": "1px",
                    "height": f"{TRANSFORMATION_NODE_HEIGHT}px",
                    "padding": "0",
                    "border": "none",
                    "background": "transparent",
                    "boxShadow": "none",
                    "opacity": 0,          # also hides the connection handles
                    "pointerEvents": "none",
                },
            )
        )
        return waypoint_id

    EDGE_STYLE = {
        "stroke": TRANSFORMATION_EDGE_COLOR, "strokeWidth": 1.5, "cursor": "none",
    }

    sf_edges = []
    for i, edge in enumerate(trans_edges):
        waypoint_id = _waypoint(edge)

        if waypoint_id:
            # The run up to the turn: no arrow head and no chip, since it is
            # the same edge continuing.
            sf_edges.append(
                StreamlitFlowEdge(
                    id=f"te{i}_run",
                    source=edge.source,
                    target=waypoint_id,
                    edge_type="smoothstep",
                    style=EDGE_STYLE,
                )
            )

        sf_edges.append(
            StreamlitFlowEdge(
                id=f"te{i}",
                source=waypoint_id or edge.source,
                target=edge.target,
                edge_type="smoothstep",
                style=EDGE_STYLE,
                marker_end={
                    "type": "arrowclosed", "color": TRANSFORMATION_EDGE_COLOR,
                },
                label_style={'fontSize': '14px', 'fill': 'blue', 'padding': '4px'},
                label=edge.label or None,
                label_show_bg=True,
                label_bg_style={'stroke': 'orange', 'fill': '#FFFFFF'},
                # An edge label is SVG text and cannot carry a data attribute,
                # but React Flow renders the edge's ariaLabel on the edge
                # element -- where the tooltip overlay picks the detail up.
                ariaLabel=edge.description or None,
            )
        )

    return sf_nodes + waypoints, sf_edges
