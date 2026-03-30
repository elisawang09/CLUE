"""
graph_utils.py
--------------
Graph traversal helpers and streamlit-flow-component builder.

No rendering library is imported here — pure graph logic only.
`build_streamlit_flow_elements()` produces the StreamlitFlowNode /
StreamlitFlowEdge lists consumed by `components/provenance_graph.py`.
"""

from __future__ import annotations

from collections import defaultdict
import os
from typing import Optional

from data.graph_data import EDGES, NODES, NodeType

# ---------------------------------------------------------------------------
# Layout constants  (logical grid → pixels)
# ---------------------------------------------------------------------------

X_SCALE  = 260   # horizontal spacing between columns
Y_SCALE  = 85   # vertical spacing between rows
X_OFFSET = 10
Y_OFFSET = 60

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

COLORS = {
    # Root (PLTV orange box)
    "root_bg":     "#F4A23A", "root_border": "#C97A10", "root_text": "#FFFFFF",
    # Operator diamond
    "op_bg":       "#F5E6C8", "op_border":   "#C9A84C", "op_text":   "#8B6914",
    # Metric pill (#)
    "metric_bg":   "#EEF0FF", "metric_border": "#6B72D9", "metric_text": "#2A2E8C",
    # Ratio pill (%)
    "ratio_bg":    "#E8F8EF", "ratio_border":  "#3DAA6B", "ratio_text":  "#1A6640",
    # Highlight (path)
    "hl_bg":       "#DBEAFE", "hl_border":   "#2563EB", "hl_text":   "#1D4ED8",
    # Edges
    "edge_normal": "#CBD5E1", "edge_hl":     "#2563EB",
}

# ---------------------------------------------------------------------------
# Adjacency helpers
# ---------------------------------------------------------------------------

def _build_adjacency() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    children: dict[str, list[str]] = defaultdict(list)
    parents:  dict[str, list[str]] = defaultdict(list)
    for e in EDGES:
        children[e.source].append(e.target)
        parents[e.target].append(e.source)
    return dict(children), dict(parents)


CHILDREN, PARENTS = _build_adjacency()


def ancestors_of(node_id: str) -> set[str]:
    """Return all ancestor node IDs inclusive of the node itself."""
    visited: set[str] = set()
    stack = [node_id]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        stack.extend(PARENTS.get(cur, []))
    return visited


def path_edges(node_id: str) -> set[tuple[str, str]]:
    """Return (source, target) pairs on the root-to-node path."""
    anc = ancestors_of(node_id)
    return {(e.source, e.target) for e in EDGES if e.source in anc and e.target in anc}


# ---------------------------------------------------------------------------
# SVG icon builders
# ---------------------------------------------------------------------------

def _operator_svg_icon(symbol: str, highlighted: bool = False) -> str:
    """
    Return an SVG string for an operator node (rotated 45°).

    Parameters
    ----------
    symbol : str
        The operator symbol (e.g., "×", "+", "−").
    highlighted : bool
        Whether the node is highlighted on the path.
    """
    color = "#1D4ED8" if highlighted else "#8B6914"
    bg_color = "#DBEAFE" if highlighted else "#F5E6C8"
    border_color = "#2563EB" if highlighted else "#C9A84C"

    size = 70
    half = size / 2
    rect_size = 28  # Diamond rect size (adjust this to make diamond bigger/smaller)
    rect_half = rect_size / 2

    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
        <g transform="rotate(45 {half} {half})">
            <rect x="{half - rect_half}" y="{half - rect_half}" width="{rect_size}" height="{rect_size}" fill="{bg_color}" stroke="{border_color}" stroke-width="2" rx="2"/>
        </g>
            <text x="{half}" y="{half}" font-size="20" font-weight="700" text-anchor="middle" dominant-baseline="middle" fill="{color}">
                {symbol}
            </text>
    </svg>'''

# ---------------------------------------------------------------------------
# Node style builders
# ---------------------------------------------------------------------------

def _node_style(node, highlighted: bool) -> dict:
    """Return a CSS-style dict for a StreamlitFlowNode."""
    if highlighted:
        base = {
            "background":   COLORS["hl_bg"],
            "border":       f"2.5px solid {COLORS['hl_border']}",
            "color":        COLORS["hl_text"],
            "boxShadow":    f"0 0 0 3px #BFDBFE",
            "fontSize":     "14px",
            "fontWeight":   "600",
        }
    elif node.node_type == NodeType.ROOT:
        base = {
            "background": COLORS["root_bg"],
            "border":     f"2px solid {COLORS['root_border']}",
            "color":      COLORS["root_text"],
            "fontWeight": "700",
            "fontSize":   "15px",
        }
    elif node.node_type == NodeType.OPERATOR:
        base = {
            "background": "transparent",
            "border":     "none",
            "color":      COLORS["op_text"],
            "height":     "40px",
            "width":      "70px",
            "display":    "flex",
            "alignItems": "center",
            "justifyContent": "center",
        }
    elif node.node_type == NodeType.RATIO:
        base = {
            "background":  COLORS["ratio_bg"],
            "border":      f"1.5px solid {COLORS['ratio_border']}",
            "color":       COLORS["ratio_text"],
            "fontSize":    "14px",
            "fontWeight":  "500",
        }
    else:  # METRIC
        base = {
            "background":  COLORS["metric_bg"],
            "border":      f"1.5px solid {COLORS['metric_border']}",
            "color":       COLORS["metric_text"],
            "fontSize":    "14px",
            "fontWeight":  "500",
        }

    # Shared base styles for all node types
    if node.node_type != NodeType.OPERATOR and node.node_type != NodeType.ROOT:
        base.update({
            "borderRadius":  "999px",
            "padding":       "8px 16px",
            "cursor":        "pointer",
            "whiteSpace":    "nowrap",
            "display":       "flex",
            "alignItems":    "center",
            "justifyContent": "center",
            "height":        "40px",
            "minWidth":      "auto",
            "maxWidth":      "250px",
        })
    else:
        base.update({
            "cursor": "pointer",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
        })

    return base


def _node_label(node, highlighted: bool = False) -> str:
    """Build the display label for a node."""
    if node.node_type == NodeType.OPERATOR:
        return _operator_svg_icon(node.symbol or "", highlighted)

    # For metric nodes, use HTML entity for # to prevent Markdown interpretation
    if node.node_type == NodeType.METRIC and node.symbol == "#":
        return f"&#35;&nbsp;&nbsp;{node.label}"

    if node.symbol:
        return f"{node.symbol}  {node.label}"
    return node.label


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_streamlit_flow_elements(
    highlighted_node: Optional[str] = None,
) -> tuple[list, list]:
    """
    Build and return (nodes, edges) lists of StreamlitFlowNode /
    StreamlitFlowEdge objects ready to pass to streamlit_flow().

    Parameters
    ----------
    highlighted_node:
        Leaf node id whose root-to-leaf path should be highlighted.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode

    h_nodes: set[str] = set()
    h_edges: set[tuple[str, str]] = set()
    if highlighted_node:
        h_nodes = ancestors_of(highlighted_node)
        h_edges = path_edges(highlighted_node)

    # ---- Nodes ----
    sf_nodes = []
    for node in NODES:
        highlighted = node.id in h_nodes

        sf_nodes.append(
            StreamlitFlowNode(
                id=node.id,
                pos=(
                    X_OFFSET + node.x * X_SCALE,
                    Y_OFFSET + node.y * Y_SCALE,
                ),
                data={"label": _node_label(node, highlighted)},
                node_type="default",
                source_position="right",
                target_position="left",
                draggable=False,
                style=_node_style(node, highlighted),
            )
        )

    # ---- Edges ----
    sf_edges = []
    for i, edge in enumerate(EDGES):
        on_path = (edge.source, edge.target) in h_edges
        sf_edges.append(
            StreamlitFlowEdge(
                id=f"e{i}",
                source=edge.source,
                target=edge.target,
                edge_type="smoothstep",
                animated=on_path,
                style={
                    "stroke":      COLORS["edge_hl"] if on_path else COLORS["edge_normal"],
                    "strokeWidth": 2.5              if on_path else 1.5,
                },
                marker_end={"type": "arrowclosed",
                             "color": COLORS["edge_hl"] if on_path else COLORS["edge_normal"]},
            )
        )

    return sf_nodes, sf_edges


# ---------------------------------------------------------------------------
# Transformation graph builder
# ---------------------------------------------------------------------------

def build_transformation_flow_elements(
    leaf_node_id: Optional[str] = None,
) -> tuple[list, list]:
    """
    Build and return (nodes, edges) lists for a transformation flow graph.

    This renders the data transformation pipeline for a specific leaf node,
    showing source tables, filters, joins, aggregations, and outputs.

    Parameters
    ----------
    leaf_node_id:
        The leaf node ID whose transformation flow should be rendered.
        If None or not found, returns empty lists.
    """
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
    from data.graph_data import TRANSFORMATION_FLOWS

    # Get the absolute path to icons directory
    from pathlib import Path
    icons_dir = Path(__file__).resolve().parent / "icons"

    if not leaf_node_id or leaf_node_id not in TRANSFORMATION_FLOWS:
        return [], []

    trans_nodes, trans_edges = TRANSFORMATION_FLOWS[leaf_node_id]

    # Transformation-specific colors
    trans_colors = {
        "source_table":  {"bg": "#F0F7FF", "border": "#0284C7", "text": "#0C4A6E"},
        "filter":        {"bg": "#FEF3C7", "border": "#D97706", "text": "#92400E"},
        "join":          {"bg": "#E0E7FF", "border": "#6366F1", "text": "#312E81"},
        "aggregation":   {"bg": "#DCF5E3", "border": "#059669", "text": "#064E3B"},
        "new_column":    {"bg": "#FCE7F3", "border": "#EC4899", "text": "#831843"},
        "output":        {"bg": "#F3E8FF", "border": "#A855F7", "text": "#581C87"},
    }

    # Layout constants for transformation graph
    tx_scale = 280
    ty_scale = 100
    tx_offset = 20
    ty_offset = 40

    STATIC_URL = "http://localhost:8502/app/static"

    sf_nodes = []
    for node in trans_nodes:
        color_key = node.node_type.value
        colors = trans_colors.get(color_key, trans_colors["source_table"])

        # Build HTML with icon - simplify to avoid encoding issues
        node_html = "<div style='display:flex; align-items:center; gap:8px; font-size:13px;'>"

        if node.icon:
            node_html += f'<img src="{STATIC_URL}/{node.icon}" width="18" height="18" style="flex-shrink:0"/>'
        else:
            node_html += "<span style='font-size:14px;'>📊</span>"

        node_html += f"<span>{node.label}</span></div>"

        sf_nodes.append(
            StreamlitFlowNode(
                id=node.id,
                pos=(
                    tx_offset + node.x * tx_scale,
                    ty_offset + node.y * ty_scale,
                ),
                data={"content": node_html},
                node_type="default",
                source_position="right",
                target_position="left",
                draggable=False,
                style={
                    "background": colors["bg"],
                    "border": f"2px solid {colors['border']}",
                    "color": colors["text"],
                    "borderRadius": "8px",
                    "padding": "10px 12px",
                    "fontSize": "13px",
                    "fontWeight": "500",
                    "cursor": "default",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "whiteSpace": "nowrap",
                    "maxWidth": "200px",
                    "minWidth": "130px",
                }
            )
        )

    # ---- Build edges ----
    sf_edges = []
    for i, edge in enumerate(trans_edges):
        sf_edges.append(
            StreamlitFlowEdge(
                id=f"te{i}",
                source=edge.source,
                target=edge.target,
                edge_type="smoothstep",
                style={
                    "stroke": "#94A3B8",
                    "strokeWidth": 1.5,
                },
                marker_end={"type": "arrowclosed", "color": "#94A3B8"},
                label=edge.label if edge.label else None,
            )
        )

    return sf_nodes, sf_edges