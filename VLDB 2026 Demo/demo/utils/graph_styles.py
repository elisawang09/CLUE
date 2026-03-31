"""
graph_styles.py
---------------
Color palette, SVG icon builders, and node style/label builders for all
graph types (provenance, simulation, transformation).

No streamlit-flow types are imported here — this module only produces
plain dicts and HTML strings that the builders in graph_builders.py
pass into StreamlitFlowNode/Edge constructors.
"""

from __future__ import annotations

from platform import node
from typing import Optional
from data.graph_data import NodeType
from data.graph_data import DeltaDirection, NodeType, SimulationDelta


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # Root (PLTV orange box)
    "root_bg":      "#FCE4C6",
    "root_border":  "#F4A23A",
    "root_text":    "#C97A10",
    # Operator diamond
    "op_bg":        "#F5E6C8",
    "op_border":    "#C9A84C",
    "op_text":      "#8B6914",
    # Metric pill (#)
    "metric_bg":    "#EEF0FF",
    "metric_border":"#6B72D9",
    "metric_text":  "#2A2E8C",
    # Ratio pill (%)
    "ratio_bg":     "#E8F8EF",
    "ratio_border": "#3DAA6B",
    "ratio_text":   "#1A6640",
    # Highlight (path)
    "hl_bg":        "#DBEAFE",
    "hl_border":    "#2563EB",
    "hl_text":      "#1D4ED8",
    # Edges
    "edge_normal":  "#CBD5E1",
    "edge_hl":      "#2563EB",
    # Simulation delta
    "delta_up":     "#16A34A",  # green
    "delta_down":   "#DC2626",  # red
    "delta_flat":   "#9CA3AF",  # grey
}

# Transformation node colors keyed by TransformationNodeType.value
TRANSFORMATION_COLORS: dict[str, dict[str, str]] = {
    "source_table": {"bg": "#F0F7FF", "border": "#0284C7", "text": "#2F2F2F"},
    "filter_table":   {"bg": "#FEF3C7", "border": "#D97706", "text": "#256AFF"},
    "new_column":   {"bg": "#FCE7F3", "border": "#EC4899", "text": "#256AFF"},
    "join":         {"bg": "#E0E7FF", "border": "#6366F1", "text": "#4E9D26"},
    "aggregation":  {"bg": "#DCF5E3", "border": "#059669", "text": "#900B09"},
    "output":       {"bg": "#F3E8FF", "border": "#A855F7", "text": "#392C05"},
}


# ---------------------------------------------------------------------------
# SVG icon builder
# ---------------------------------------------------------------------------

def operator_svg_icon(symbol: str, highlighted: bool = False) -> str:
    """Return an SVG string for a diamond-shaped operator node."""
    color        = "#1D4ED8" if highlighted else COLORS["op_text"]
    bg_color     = "#DBEAFE" if highlighted else COLORS["op_bg"]
    border_color = "#2563EB" if highlighted else COLORS["op_border"]

    size      = 40
    half      = size / 2
    rect_size = 28
    rect_half = rect_size / 2

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="rotate(45 {half} {half})">'
        f'<rect x="{half - rect_half}" y="{half - rect_half}" '
        f'width="{rect_size}" height="{rect_size}" '
        f'fill="{bg_color}" stroke="{border_color}" stroke-width="2" rx="2"/>'
        f'</g>'
        f'<text x="{half}" y="{half}" font-size="20" font-weight="700" '
        f'text-anchor="middle" dominant-baseline="middle" fill="{color}">'
        f'{symbol}'
        f'</text>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# Node style builders
# ---------------------------------------------------------------------------

def node_style(node, highlighted: bool) -> dict:
    """Return a CSS-style dict for a provenance graph StreamlitFlowNode."""
    base: dict = {
        "cursor":          "pointer",
        "display":         "flex",
        "alignItems":      "center",
        "justifyContent":  "center",
        "height":          "50px",
    }

    if node.node_type == NodeType.ROOT:
        base.update({
            "background": COLORS["root_bg"],
            "border":     f"3px solid {COLORS['root_border']}",
            "color":      COLORS["root_text"],
            "fontWeight": "700",
            "fontSize":   "16px",
        })
    elif node.node_type == NodeType.OPERATOR:
        base.update({
            "background":     "transparent",
            "border":         "none",
            "color":          COLORS["op_text"],
            "padding":          "2px",
            "display":        "flex",
            "alignItems":     "center",
            "justifyContent": "center",
        })
    elif node.node_type == NodeType.RATIO:
        base.update({
            "background": COLORS["ratio_bg"],
            "border":     f"1.5px solid {COLORS['ratio_border']}",
            "color":      COLORS["ratio_text"],
            "fontSize":   "14px",
            "fontWeight": "500",
        })
    else:  # METRIC
        base.update({
            "background": COLORS["metric_bg"],
            "border":     f"1.5px solid {COLORS['metric_border']}",
            "color":      COLORS["metric_text"],
            "fontSize":   "14px",
            "fontWeight": "500",
        })

    if highlighted and node.node_type != NodeType.OPERATOR:
        base["border"] = f"3.5px solid {COLORS['hl_border']}"

    if node.node_type not in (NodeType.OPERATOR, NodeType.ROOT):
        base.update({
            "borderRadius": "999px",
            "padding":      "8px 16px",
            "cursor":       "pointer",
            "whiteSpace":   "nowrap",
            "minWidth":     "auto",
            "maxWidth":     "250px",
        })

    return base


def node_style_sim(node) -> dict:
    """
    Return a CSS-style dict for a simulation graph node.

    For simulation nodes, we keep the same lean size as provenance nodes.
    Delta information is positioned outside the node shape via the label's
    CSS flex layout.
    """
    style = node_style(node, highlighted=False)
    style['height'] = '60px'
    return style


# ---------------------------------------------------------------------------
# Node label builders
# ---------------------------------------------------------------------------

def node_label(node, highlighted: bool = False) -> str:
    """Build the display label string for a provenance graph node."""
    if node.node_type == NodeType.OPERATOR:
        return operator_svg_icon(node.symbol or "", highlighted)

    if node.node_type == NodeType.METRIC and node.symbol == "#":
        raw = f"&#35;&nbsp;&nbsp;{node.label}"
    elif node.symbol:
        raw = f"{node.symbol}  {node.label}"
    else:
        raw = node.label

    if node.description:
        tip = node.description.replace('"', '&quot;')
        return f'<span data-flow-tooltip="{tip}">{raw}</span>'
    return raw


def _delta_html(delta: SimulationDelta) -> str:
    """
    Build an HTML wrapper showing the simulation delta badge for a node.

    The returned string contains a ``{label_placeholder}`` token that the
    caller replaces with the actual node label text.

    For leaf nodes: delta is positioned to the right, left-aligned.
    For non-leaf nodes: delta is positioned below, center-aligned.

    Parameters
    ----------
    delta : The delta data for this node.
    """
    dir_map = {
        DeltaDirection.UP:   ("↑", COLORS["delta_up"]),
        DeltaDirection.DOWN: ("↓", COLORS["delta_down"]),
        DeltaDirection.FLAT: ("—", COLORS["delta_flat"]),
    }
    arrow, color = dir_map[delta.direction]

    if delta.direction == DeltaDirection.FLAT:
        value_html = ""
    else:
        value_html = (
            f'<span style="color:{color}; font-weight:700; font-size:12px;">'
            f'{arrow}&nbsp;{delta.new_value}'
            f'</span>&nbsp;'
        )

    prev_html = (
        f'<span style="color:{COLORS["delta_flat"]}; font-size:11px;">'
        f'({delta.label_prefix}&nbsp;{delta.prev_value})'
        f'</span>'
    )

    if delta.direction == DeltaDirection.FLAT:
        badge = (
            f'<span style="color:{color}; font-weight:700; font-size:12px;">{arrow}</span>'
            f'&nbsp;{prev_html}'
        )
    else:
        badge = f'{value_html}{prev_html}'

    return (
        f'<div style="display:flex; flex-direction:column; align-items:center; gap:2px;">'
        f'<span style="white-space:nowrap; margin:0;">{{label_placeholder}}</span>'
        f'<span style="white-space:nowrap; font-size:12px; text-align:center; margin:0;">{badge}</span>'
        f'</div>'
    )


def node_label_sim(
    node,
    delta: Optional[SimulationDelta]
) -> str:
    """
    Build the display label for a simulation graph node.

    Wraps the standard provenance label with a delta badge when a
    SimulationDelta is provided.
    """
    if node.node_type == NodeType.OPERATOR:
        return operator_svg_icon(node.symbol or "", highlighted=False)

    base = node_label(node, highlighted=False)

    if delta is None:
        return base

    return _delta_html(delta).replace("{label_placeholder}", base)


# ---------------------------------------------------------------------------
# Transformation node HTML builder
# ---------------------------------------------------------------------------

def transformation_node_html(node, static_url: str) -> str:
    """Build the inner HTML string for a transformation flow node."""
    ICON_SIZE = 50

    tip = f'data-flow-tooltip="{node.description.replace(chr(34), "&quot;")}"' if node.description else ''
    html = f'<div class="node_label" style="display:flex; flex-direction:column; align-items:center; gap:2px; font-size:15px;" {tip}>'
    if node.icon:
        html += (
            f'<img src="{static_url}/{node.icon}" width={ICON_SIZE} height={ICON_SIZE} '
            f'style="flex-shrink:0; margin:0;"/>'
        )
    else:
        html += "<span style='font-size:15px;'>📊</span>"
    html += f"<span style='margin:0;'>{node.label}</span></div>"

    return html


def transformation_node_style(node) -> dict:
    """Return a CSS-style dict for a transformation flow node."""
    colors = TRANSFORMATION_COLORS.get(node.node_type.value, TRANSFORMATION_COLORS["source_table"])
    return {
        "background":     "transparent",
        "border":         "none",
        "color":          colors["text"],
        "borderRadius":   "8px",
        "padding":        "2px",
        "fontSize":       "15px",
        "fontWeight":     "500",
        "cursor":         "default",
        "display":        "flex",
        "alignItems":     "center",
        "justifyContent": "center",
        "whiteSpace":     "nowrap",
        "maxWidth":       "200px",
        "minWidth":       "130px",
    }

# ---------------------------------------------------------------------------
# Legend style
# ---------------------------------------------------------------------------

def legend_style_html() -> str:
    """Inject CSS to hide the StreamlitFlow minimap and controls."""

    return f"""
            <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:8px;padding:7px 14px;
                        background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                        font-size:0.8rem;color:#374151;align-items:center">
            <span><span style="background:{COLORS['root_bg']}; border:3px solid {COLORS['root_border']};border-radius:4px;
                padding:1px 8px; color:{COLORS['root_text']}; font-weight:700">PLTV</span>&nbsp; Root</span>
            <span><span style="background:{COLORS['op_bg']};border:1.5px solid {COLORS['op_border']};
                border-radius:4px;padding:1px 8px;color:{COLORS['op_text']}">&times; &div;</span>&nbsp; Operator</span>
            <span><span style="background:{COLORS['ratio_bg']};border:1.5px solid {COLORS['ratio_border']};
                border-radius:20px;padding:1px 10px;color:{COLORS['ratio_text']}">% Metric</span>&nbsp; Ratio</span>
            <span><span style="background:{COLORS['metric_bg']};border:1.5px solid {COLORS['metric_border']};
                border-radius:20px;padding:1px 10px;color:{COLORS['metric_text']}"># Metric</span>&nbsp; Count/value</span>
            <span><span style="display:inline-block;width:28px;height:3px;background:{COLORS['edge_hl']};
                vertical-align:middle;border-radius:2px"></span>&nbsp; Highlighted path</span>
            </div>
            """


def transformation_legend_style_html() -> str:
    """Build the legend for transformation flow nodes."""
    ICON_SIZE = 24
    STATIC_URL = "http://localhost:8502/app/static"

    transform_types = [
        ("source_table", "Source Table"),
        ("filter_table", "Row Removal"),
        ("new_column", "New Column"),
        ("join", "Join"),
        ("aggregation", "Aggregations"),
        ("output", "Output Metric"),
    ]

    legend_items = []
    for node_type, label in transform_types:
        colors = TRANSFORMATION_COLORS[node_type]
        icon_path = f"{STATIC_URL}/{node_type}.png"
        legend_items.append(
            f'<span style="display:flex;align-items:center;gap:6px;">'
            f'<img src="{icon_path}" width={ICON_SIZE} height={ICON_SIZE} style="flex-shrink:0;"/>'
            f'{label}</span>'
        )

    return f"""
            <div style="display:flex;gap:15px;flex-wrap:wrap;margin-top:8px;padding:7px 14px;
                        background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                        font-size:0.85rem;color:#374151;align-items:center">
            {' '.join(legend_items)}
            </div>
            """