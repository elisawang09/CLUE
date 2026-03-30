"""
graph_data.py
-------------
Static graph definition for the PLTV metric provenance graph.
Defines node types, symbols, and edges that describe how PLTV is computed.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NodeType(str, Enum):
    ROOT = "root"           # The primary metric (e.g. PLTV) - orange box
    OPERATOR = "operator"   # Arithmetic operator diamond (×, ÷)
    METRIC = "metric"       # A sub-metric circle with # symbol
    RATIO = "ratio"         # A ratio/percentage metric with % symbol


@dataclass
class Node:
    id: str
    label: str
    node_type: NodeType
    symbol: Optional[str] = None        # "#", "%", "×", "÷", etc.
    description: Optional[str] = None   # Tooltip / detail text
    x: float = 0.0                      # Layout hint (logical column)
    y: float = 0.0                      # Layout hint (logical row)


@dataclass
class Edge:
    source: str
    target: str


class TransformationNodeType(str, Enum):
    SOURCE_TABLE = "source_table"    # Source data tables (with icon)
    FILTER = "filter"               # Filter/transformation operations
    JOIN = "join"                   # Join operations
    AGGREGATION = "aggregation"     # SUM, COUNT, AVG, etc.
    NEW_COLUMN = "new_column"       # Derived/computed columns
    OUTPUT = "output"               # Output table


@dataclass
class TransformationNode:
    """Node in a data transformation flow."""
    id: str
    label: str
    node_type: TransformationNodeType
    description: Optional[str] = None
    icon: Optional[str] = None              # PNG icon filename or path
    x: float = 0.0
    y: float = 0.0


@dataclass
class TransformationEdge:
    """Edge in a data transformation flow."""
    source: str
    target: str
    label: Optional[str] = None             # SQL operation or transformation label
    icon: Optional[str] = None              # Optional icon filename to display on edge


# ---------------------------------------------------------------------------
# Node definitions
# ---------------------------------------------------------------------------

NODES: list[Node] = [
    # Root
    Node(
        id="pltv",
        label="PLTV",
        node_type=NodeType.ROOT,
        description="Predicted Lifetime Value – estimates how much revenue a typical customer generates over their lifetime.",
        x=0, y=2,
    ),

    # Operators (diamonds)
    Node(id="op_mul",  label="", node_type=NodeType.OPERATOR, symbol="×", x=1, y=2),
    Node(id="op_div1", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=0),
    Node(id="op_div2", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=2),
    Node(id="op_div3", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=4),

    # Mid-level metrics
    Node(
        id="prob_active",
        label="Probability of Active",
        node_type=NodeType.RATIO,
        symbol="%",
        description="Probability that a customer segment remains active in a given period.",
        x=2, y=0,
    ),
    Node(
        id="exp_orders",
        label="Expected Number of Orders",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Expected number of orders placed by an active customer.",
        x=2, y=2,
    ),
    Node(
        id="exp_order_value",
        label="Expected Order Value",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Expected monetary value of a single order.",
        x=2, y=4,
    ),

    # Leaf metrics
    Node(
        id="active_customers_1",
        label="Active Customers",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Number of customers who placed at least one order in the period.",
        x=4, y=-0.5,
    ),
    Node(
        id="acquired_customers",
        label="Acquired Customers",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Number of new customers acquired during the period.",
        x=4, y=0.5,
    ),
    Node(
        id="total_orders",
        label="Total Orders",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Total number of orders placed by active customers.",
        x=4, y=1.5,
    ),
    Node(
        id="active_customers_2",
        label="Active Customers",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Number of customers who placed at least one order in the period.",
        x=4, y=2.5,
    ),
    Node(
        id="total_gross_order_value",
        label="Total Gross Order Value",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Sum of gross value across all orders.",
        x=4, y=3.5,
    ),
    Node(
        id="total_orders_2",
        label="Total Orders",
        node_type=NodeType.METRIC,
        symbol="#",
        description="Total number of orders placed.",
        x=4, y=4.5,
    ),
]

# ---------------------------------------------------------------------------
# Edge definitions  (source → target)
# ---------------------------------------------------------------------------

EDGES: list[Edge] = [
    # PLTV → multiply operator
    Edge("pltv", "op_mul"),

    # multiply operator feeds three mid-level metrics
    Edge("op_mul", "prob_active"),
    Edge("op_mul", "exp_orders"),
    Edge("op_mul", "exp_order_value"),

    # prob_active → div1 → leaves
    Edge("prob_active", "op_div1"),
    Edge("op_div1", "active_customers_1"),
    Edge("op_div1", "acquired_customers"),

    # exp_orders → div2 → leaves
    Edge("exp_orders", "op_div2"),
    Edge("op_div2", "total_orders"),
    Edge("op_div2", "active_customers_2"),

    # exp_order_value → div3 → leaves
    Edge("exp_order_value", "op_div3"),
    Edge("op_div3", "total_gross_order_value"),
    Edge("op_div3", "total_orders_2"),
]

# ---------------------------------------------------------------------------
# Quick lookup helpers
# ---------------------------------------------------------------------------

NODE_MAP: dict[str, Node] = {n.id: n for n in NODES}

LEAF_IDS: set[str] = {
    n.id for n in NODES
    if not any(e.source == n.id for e in EDGES)
}

# ---------------------------------------------------------------------------
# Transformation flow data for each leaf metric
# ---------------------------------------------------------------------------
# Each leaf node can show a detailed transformation flow showing how that
# metric is computed from raw tables.

TRANSFORMATION_FLOWS: dict[str, tuple[list[TransformationNode], list[TransformationEdge]]] = {
    # "active_customers_1": Active Customers (from prob_active path)
    "active_customers_1": (
        [
            TransformationNode(
                id="raw_orders",
                label="raw_orders",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all orders",
                icon="source_table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="recent_odr",
                label="recent_odr",
                node_type=TransformationNodeType.FILTER,
                description="Filter: Recent orders only",
                x=1, y=0
            ),
            TransformationNode(
                id="active_customers",
                label="Active Customers",
                node_type=TransformationNodeType.OUTPUT,
                description="Count of unique customers",
                icon="output.png",
                x=2, y=0
            ),
        ],
        [
            TransformationEdge("raw_orders", "recent_odr", "Filter applied"),
            TransformationEdge("recent_odr", "active_customers", "COUNT(DISTINCT customer_id)"),
        ]
    ),

    # "acquired_customers": Acquired Customers (from prob_active path)
    "acquired_customers": (
        [
            TransformationNode(
                id="raw_customers",
                label="raw_customers",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all customers",
                icon="table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="new_customers",
                label="New Customers",
                node_type=TransformationNodeType.FILTER,
                description="Filter: acquisition_date in period",
                x=1, y=0
            ),
            TransformationNode(
                id="acquired_count",
                label="Acquired Customers",
                node_type=TransformationNodeType.OUTPUT,
                description="Count of acquired customers",
                icon="table.png",
                x=2, y=0
            ),
        ],
        [
            TransformationEdge("raw_customers", "new_customers", "Filter applied"),
            TransformationEdge("new_customers", "acquired_count", "COUNT(*)"),
        ]
    ),

    # "total_orders": Total Orders (from exp_orders path)
    "total_orders": (
        [
            TransformationNode(
                id="raw_orders_2",
                label="raw_orders",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all orders",
                icon="table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="raw_order_items_2",
                label="raw_order_items",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Order line items",
                icon="table.png",
                x=0, y=1
            ),
            TransformationNode(
                id="recent_odr_2",
                label="recent_odr",
                node_type=TransformationNodeType.FILTER,
                description="Filter: Recent orders",
                x=1, y=0
            ),
            TransformationNode(
                id="recent_odr_items",
                label="recent_odr_items",
                node_type=TransformationNodeType.JOIN,
                description="Join with order items",
                x=1.5, y=0.5
            ),
            TransformationNode(
                id="total_orders_output",
                label="Total Orders",
                node_type=TransformationNodeType.OUTPUT,
                description="Count of orders",
                icon="table.png",
                x=2.5, y=0.25
            ),
        ],
        [
            TransformationEdge("raw_orders_2", "recent_odr_2", "Filter applied"),
            TransformationEdge("raw_order_items_2", "recent_odr_items", "Join"),
            TransformationEdge("recent_odr_2", "recent_odr_items", "Join (J)"),
            TransformationEdge("recent_odr_items", "total_orders_output", "COUNT(*)"),
        ]
    ),

    # "active_customers_2": Active Customers (from exp_orders path)
    "active_customers_2": (
        [
            TransformationNode(
                id="raw_orders_3",
                label="raw_orders",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all orders",
                icon="table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="recent_odr_3",
                label="recent_odr",
                node_type=TransformationNodeType.FILTER,
                description="Filter: Recent orders",
                x=1, y=0
            ),
            TransformationNode(
                id="active_cust_output",
                label="Active Customers",
                node_type=TransformationNodeType.OUTPUT,
                description="Count of distinct customers",
                icon="table.png",
                x=2, y=0
            ),
        ],
        [
            TransformationEdge("raw_orders_3", "recent_odr_3", "Filter applied"),
            TransformationEdge("recent_odr_3", "active_cust_output", "COUNT(DISTINCT customer_id)"),
        ]
    ),

    # "total_gross_order_value": Total Gross Order Value (from exp_order_value path)
    "total_gross_order_value": (
        [
            TransformationNode(
                id="raw_orders_4",
                label="raw_orders",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all orders",
                icon="source_table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="raw_order_items_3",
                label="raw_order_items",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Order line items",
                icon="source_table.png",
                x=0, y=1
            ),
            TransformationNode(
                id="raw_products",
                label="raw_products",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Product master data",
                icon="source_table.png",
                x=0, y=2
            ),
            TransformationNode(
                id="recent_odr_4",
                label="recent_odr",
                node_type=TransformationNodeType.FILTER,
                description="Filter: Recent orders",
                x=1, y=0
            ),
            TransformationNode(
                id="recent_odr_items_2",
                label="recent_odr_items",
                node_type=TransformationNodeType.FILTER,
                description="Filter: Recent order items",
                x=1, y=1
            ),
            TransformationNode(
                id="odr_item_prod",
                label="odr_item_products",
                node_type=TransformationNodeType.JOIN,
                description="Join with products",
                x=2, y=2
            ),
            TransformationNode(
                id="gross_value",
                label="gross_value",
                node_type=TransformationNodeType.NEW_COLUMN,
                description="SELECT (revenue - cost) AS gross_value",
                x=3, y=2
            ),
            TransformationNode(
                id="total_gross_output",
                label="Total Gross Order Value",
                node_type=TransformationNodeType.AGGREGATION,
                description="SUM(gross_value)",
                x=4, y=2
            ),
        ],
        [
            TransformationEdge("raw_orders_4", "recent_odr_4", "Filter applied"),
            TransformationEdge("raw_order_items_3", "recent_odr_items_2", "Filter applied"),
            TransformationEdge("recent_odr_4", "recent_odr_items_2", "Filter applied"),
            TransformationEdge("recent_odr_items_2", "odr_item_prod", "Join"),
            TransformationEdge("raw_products", "odr_item_prod", "Join"),
            TransformationEdge("odr_item_prod", "gross_value", "Transformation"),
            TransformationEdge("gross_value", "total_gross_output", "SUM"),
        ]
    ),

    # "total_orders_2": Total Orders (from exp_order_value path)
    "total_orders_2": (
        [
            TransformationNode(
                id="raw_orders_5",
                label="raw_orders",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="Source table containing all orders",
                icon="table.png",
                x=0, y=0
            ),
            TransformationNode(
                id="total_orders_5",
                label="Total Orders",
                node_type=TransformationNodeType.AGGREGATION,
                description="COUNT(*) of orders",
                x=1, y=0
            ),
        ],
        [
            TransformationEdge("raw_orders_5", "total_orders_5", "COUNT(*)"),
        ]
    ),
}
