"""
graph_data.py
-------------
Graph definition for the 6-Month Customer Value provenance graph.
Defines node types, symbols, edges, transformation flows, and simulation deltas.

The metric structure follows the headline formula:

    6-Month Customer Value
      = 6-Month Purchase Conversion Rate     (Purchasing Customers / Acquired Users)
      x Orders per Purchasing Customer       (Total Orders / Purchasing Customers)
      x Average Order Value                  (Total Gross Order Value / Total Orders)

Node ids are clipped word stems; they key the session-state graph caches, the
transformation flows, and the simulation deltas. Values are never written here
-- they come from data/metrics.py so the graph and the numbers cannot drift.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class NodeType(str, Enum):
    ROOT = "root"           # The primary metric (6-Month Customer Value) - orange box
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
    FILTER = "filter_table"          # Filter/transformation operations
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
    """
    Edge in a data transformation flow.

    `label` names the kind of operation ("Filter applied", "Join"); the
    predicate, join key or expression behind it goes in `description`, which
    the operation chip shows on hover. Nodes describe what a table or column
    *is*; edges describe what was *done*.
    """
    source: str
    target: str
    label: Optional[str] = None             # SQL operation or transformation label
    icon: Optional[str] = None              # Optional icon filename to display on edge
    description: Optional[str] = None       # Operation detail, shown on hover


# ---------------------------------------------------------------------------
# Node definitions
# ---------------------------------------------------------------------------
#
# Descriptions carry the definition and the formula only. The computed value is
# appended at render time from data/metrics.py.

NODES: list[Node] = [
    # Root
    Node(
        id="cust_val",
        label="6-Month Customer Value",
        node_type=NodeType.ROOT,
        description=(
            "Average value generated per acquired user during the first 6 months "
            "after acquisition. Calculated as 6-Month Purchase Conversion Rate × "
            "Orders per Purchasing Customer × Average Order Value."
        ),
        x=0, y=2,
    ),

    # Operators (diamonds)
    Node(id="op_mul",  label="", node_type=NodeType.OPERATOR, symbol="×", x=1, y=2),
    Node(id="op_div1", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=0),
    Node(id="op_div2", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=2),
    Node(id="op_div3", label="", node_type=NodeType.OPERATOR, symbol="÷", x=3, y=4),

    # The three factors
    Node(
        id="conv_rate",
        label="6-Month Purchase Conversion Rate",
        node_type=NodeType.RATIO,
        symbol="%",
        description=(
            "Share of acquired users who place at least one order within their "
            "first 6 months. Calculated as Purchasing Customers ÷ Acquired Users."
        ),
        x=2, y=0,
    ),
    Node(
        id="orders_per_cust",
        label="Orders per Purchasing Customer",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Average number of orders placed by a customer who ordered at least "
            "once in their first 6 months. Users who never ordered are excluded "
            "from this average. Calculated as Total Orders ÷ Purchasing Customers."
        ),
        x=2, y=2,
    ),
    Node(
        id="avg_order_val",
        label="Average Order Value",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Average gross value of a single qualifying order. Calculated as "
            "Total Gross Order Value ÷ Total Orders."
        ),
        x=2, y=4,
    ),

    # Leaf metrics
    Node(
        id="purch_cust_1",
        label="Purchasing Customers",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Acquired users with at least one qualifying order during their first "
            "6 months after acquisition."
        ),
        x=4, y=-0.5,
    ),
    Node(
        id="acq_users",
        label="Acquired Users",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Users acquired during the reference acquisition period, whether or "
            "not they went on to order. Non-purchasing users stay in the "
            "denominator of the metric."
        ),
        x=4, y=0.5,
    ),
    Node(
        id="tot_orders_1",
        label="Total Orders",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Orders placed by the acquisition group, counting only orders within "
            "each user's own first 6 months."
        ),
        x=4, y=1.5,
    ),
    Node(
        id="purch_cust_2",
        label="Purchasing Customers",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Acquired users with at least one qualifying order during their first "
            "6 months after acquisition."
        ),
        x=4, y=2.5,
    ),
    Node(
        id="tot_gross_val",
        label="Total Gross Order Value",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Gross value of all qualifying orders, summed across every order "
            "line, where gross_value = revenue − cost."
        ),
        x=4, y=3.5,
    ),
    Node(
        id="tot_orders_2",
        label="Total Orders",
        node_type=NodeType.METRIC,
        symbol="#",
        description=(
            "Orders placed by the acquisition group, counting only orders within "
            "each user's own first 6 months."
        ),
        x=4, y=4.5,
    ),
]

# ---------------------------------------------------------------------------
# Edge definitions  (source → target)
# ---------------------------------------------------------------------------

EDGES: list[Edge] = [
    # 6-Month Customer Value → multiply operator
    Edge("cust_val", "op_mul"),

    # multiply operator feeds the three factors
    Edge("op_mul", "conv_rate"),
    Edge("op_mul", "orders_per_cust"),
    Edge("op_mul", "avg_order_val"),

    # conversion rate = purchasing customers ÷ acquired users
    Edge("conv_rate", "op_div1"),
    Edge("op_div1", "purch_cust_1"),
    Edge("op_div1", "acq_users"),

    # orders per purchasing customer = total orders ÷ purchasing customers
    Edge("orders_per_cust", "op_div2"),
    Edge("op_div2", "tot_orders_1"),
    Edge("op_div2", "purch_cust_2"),

    # average order value = total gross order value ÷ total orders
    Edge("avg_order_val", "op_div3"),
    Edge("op_div3", "tot_gross_val"),
    Edge("op_div3", "tot_orders_2"),
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
# Simulation delta data
# ---------------------------------------------------------------------------

class DeltaDirection(str, Enum):
    UP = "up"       # Green arrow up
    DOWN = "down"   # Red arrow down
    FLAT = "flat"   # Grey dash (no change)


@dataclass
class SimulationDelta:
    """
    Captures the simulated change for a single node.

    Attributes
    ----------
    node_id : str
        Matches a Node.id from NODES.
    delta_value : str
        Formatted change shown in bold (e.g. "$24", "0.2", "400").
    prev_value : str
        Formatted historical baseline value shown in parentheses.
    direction : DeltaDirection
        Visual indicator: UP (green ↑), DOWN (red ↓), or FLAT (grey —).
    label_prefix : str
        Short label preceding prev_value, either "Baseline:" or "Curr:".
    """
    node_id: str
    delta_value: str
    prev_value: str
    direction: DeltaDirection
    label_prefix: str = "Baseline:"
    description: Optional[str] = None   # Optional detailed description for tooltip


def _delta(
    node_id: str,
    scenario: float,
    baseline: float,
    fmt,
    description: str,
    label_prefix: str = "Baseline:",
) -> SimulationDelta:
    """Build a delta badge from a scenario value and its baseline counterpart."""
    change = scenario - baseline
    if abs(change) < 1e-9:
        return SimulationDelta(
            node_id=node_id,
            delta_value="",
            prev_value=fmt(baseline),
            direction=DeltaDirection.FLAT,
            label_prefix=label_prefix,
            description=description,
        )
    return SimulationDelta(
        node_id=node_id,
        delta_value=fmt(abs(change)),
        prev_value=fmt(baseline),
        direction=DeltaDirection.UP if change > 0 else DeltaDirection.DOWN,
        label_prefix=label_prefix,
        description=description,
    )


def _assumption_note(baseline_value: float, scenario_value: float, fmt) -> str:
    """Tooltip text for one of the three assumptions the participant controls."""
    if abs(scenario_value - baseline_value) < 1e-9:
        return "Held at the historical baseline in this scenario."
    return (
        f"Scenario assumption: {fmt(baseline_value)} → {fmt(scenario_value)}."
    )


def simulation_deltas(baseline=None, scenario=None) -> dict[str, SimulationDelta]:
    """
    Scenario values for every provenance node, against the historical baseline.

    The scenario carries the three assumptions; everything downstream of them
    is propagated, never written down:

        Purchasing Customers    = Acquired Users x Conversion Rate
        Total Orders            = Purchasing Customers x Orders per Customer
        Total Gross Order Value = Total Orders x Average Order Value
        6-Month Customer Value  = Conversion x Orders per Customer x AOV

    With no scenario given, every assumption sits at its observed value, so the
    graph shows the baseline against itself. The baseline is never modified.
    """
    from data.metrics import count, decimal, load_baseline, money, percent, whole_money
    from data.scenario import from_baseline

    base = load_baseline() if baseline is None else baseline
    plan = from_baseline(base) if scenario is None else scenario

    conv_rate = plan.conversion_rate
    orders_per_cust = plan.orders_per_purchasing_customer
    avg_order_val = plan.average_order_value
    acq_users = plan.acquired_users
    purch_cust = plan.purchasing_customers
    tot_orders = plan.total_orders
    tot_gross_val = plan.total_gross_order_value
    cust_val = plan.customer_value

    deltas = {
        "cust_val": _delta(
            "cust_val", cust_val, base.customer_value, money,
            f"Scenario result: {money(base.customer_value)} → {money(cust_val)} "
            f"(= {percent(conv_rate)} × {decimal(orders_per_cust)} × {money(avg_order_val)}).",
        ),
        "conv_rate": _delta(
            "conv_rate", conv_rate, base.conversion_rate, percent,
            _assumption_note(base.conversion_rate, conv_rate, percent),
        ),
        "orders_per_cust": _delta(
            "orders_per_cust", orders_per_cust, base.orders_per_purchasing_customer,
            decimal,
            _assumption_note(
                base.orders_per_purchasing_customer, orders_per_cust, decimal
            ),
        ),
        "avg_order_val": _delta(
            "avg_order_val", avg_order_val, base.average_order_value, money,
            _assumption_note(base.average_order_value, avg_order_val, money),
        ),
        "acq_users": _delta(
            "acq_users", acq_users, base.acquired_users, count,
            "Size of the acquisition group; unchanged by the scenario.",
        ),
        "tot_gross_val": _delta(
            "tot_gross_val", tot_gross_val, base.total_gross_order_value, whole_money,
            f"Computed consequence: {count(tot_orders)} orders × {money(avg_order_val)}.",
        ),
    }

    for node_id in ("purch_cust_1", "purch_cust_2"):
        deltas[node_id] = _delta(
            node_id, purch_cust, base.purchasing_customers, count,
            f"Computed consequence: {count(acq_users)} acquired users × "
            f"{percent(conv_rate)}.",
        )

    for node_id in ("tot_orders_1", "tot_orders_2"):
        deltas[node_id] = _delta(
            node_id, tot_orders, base.total_orders, count,
            f"Computed consequence: {count(purch_cust)} purchasing customers × "
            f"{decimal(orders_per_cust)} orders each.",
        )

    return deltas


# ---------------------------------------------------------------------------
# Transformation flow data for each leaf metric
# ---------------------------------------------------------------------------
#
# Four of the six leaves share the same pipeline up to "qualifying orders":
# select the acquisition group, join their orders, derive customer_age_month,
# then keep months 1-6. _acquisition_stage() builds that shared prefix so the
# flows cannot describe the population differently from one another.

_REFERENCE_PERIOD = "Jan-Mar 2022"
_QUALIFYING_ID = "qualifying"

# Both edges into a join carry the same detail, the way the original flows put
# "Join" on both. The first line of a detail is the SQL; the rest explains it.
_JOIN_ORDERS_DETAIL = (
    "FROM acquired_users LEFT JOIN raw_orders USING (user_id)\n"
    "A left join, so acquired users without orders are not dropped."
)


def _acquisition_stage(
    suffix: str,
) -> tuple[list[TransformationNode], list[TransformationEdge]]:
    """Source tables through to the qualifying orders of the acquisition group."""
    nodes = [
        TransformationNode(
            id=f"raw_customers{suffix}",
            label="raw_customers",
            node_type=TransformationNodeType.SOURCE_TABLE,
            description="One row per user, with their acquisition date.",
            icon="source_table.png",
            x=0, y=0,
        ),
        TransformationNode(
            id=f"acq_users{suffix}",
            label="acquired_users",
            node_type=TransformationNodeType.FILTER,
            description=(
                f"The users acquired in {_REFERENCE_PERIOD}, including those who "
                f"never order."
            ),
            icon="filter_table.png",
            x=1, y=0,
        ),
        TransformationNode(
            id=f"raw_orders{suffix}",
            label="raw_orders",
            node_type=TransformationNodeType.SOURCE_TABLE,
            description="One row per order, with its order date.",
            icon="source_table.png",
            x=0, y=1.2,
        ),
        TransformationNode(
            id=f"user_orders{suffix}",
            label="user_orders",
            node_type=TransformationNodeType.JOIN,
            description=(
                "Every order placed by an acquired user, alongside the acquired "
                "users who placed none."
            ),
            icon="join.png",
            x=2, y=0.6,
        ),
        TransformationNode(
            id=f"age_month{suffix}",
            label="customer_age_month",
            node_type=TransformationNodeType.NEW_COLUMN,
            description="Each order's month relative to that user's own acquisition date.",
            icon="new_column.png",
            x=3, y=0.6,
        ),
        TransformationNode(
            id=f"{_QUALIFYING_ID}{suffix}",
            label="qualifying_orders",
            node_type=TransformationNodeType.FILTER,
            description="Orders placed inside each user's own first six months.",
            icon="filter_table.png",
            x=4, y=0.6,
        ),
    ]

    edges = [
        TransformationEdge(
            f"raw_customers{suffix}", f"acq_users{suffix}", "Filter applied",
            description=(
                f"WHERE acquisition_date IN {_REFERENCE_PERIOD}\n"
                f"Every acquired user is kept, including those who never order, "
                f"so non-purchasers stay in the denominator of the metric."
            ),
        ),
        TransformationEdge(
            f"acq_users{suffix}", f"user_orders{suffix}", "Join",
            description=_JOIN_ORDERS_DETAIL,
        ),
        TransformationEdge(
            f"raw_orders{suffix}", f"user_orders{suffix}", "Join",
            description=_JOIN_ORDERS_DETAIL,
        ),
        TransformationEdge(
            f"user_orders{suffix}", f"age_month{suffix}", "New Column",
            description=(
                "SELECT MONTHS_BETWEEN(order_date, acquisition_date) + 1 "
                "AS customer_age_month\n"
                "Month 1 is acquisition_date <= order_date < acquisition_date "
                "+ 1 month."
            ),
        ),
        TransformationEdge(
            f"age_month{suffix}", f"{_QUALIFYING_ID}{suffix}", "Filter applied",
            description=(
                "WHERE customer_age_month BETWEEN 1 AND 6\n"
                "Each user is observed for their own first six months, never by "
                "calendar date, so users acquired later in the period get the "
                "same length of window."
            ),
        ),
    ]

    return nodes, edges


def _acquired_users_flow() -> tuple[list[TransformationNode], list[TransformationEdge]]:
    """Acquired Users: counted before any filtering to purchasers."""
    return (
        [
            TransformationNode(
                id="raw_customers_au",
                label="raw_customers",
                node_type=TransformationNodeType.SOURCE_TABLE,
                description="One row per user, with their acquisition date.",
                icon="source_table.png",
                x=0, y=0,
            ),
            TransformationNode(
                id="acq_users_au",
                label="acquired_users",
                node_type=TransformationNodeType.FILTER,
                description=(
                    f"The users acquired in {_REFERENCE_PERIOD}, including those "
                    f"who never order."
                ),
                icon="filter_table.png",
                x=1, y=0,
            ),
            TransformationNode(
                id="acq_users_output",
                label="Acquired Users",
                node_type=TransformationNodeType.OUTPUT,
                description=(
                    "The denominator of the metric: every user acquired in the "
                    "reference period."
                ),
                icon="output.png",
                x=2, y=0,
            ),
        ],
        [
            TransformationEdge(
                "raw_customers_au", "acq_users_au", "Filter applied",
                description=(
                    f"WHERE acquisition_date IN {_REFERENCE_PERIOD}\n"
                    f"The reference acquisition period: which users belong to "
                    f"this historical group."
                ),
            ),
            TransformationEdge(
                "acq_users_au", "acq_users_output", "Distinct Count",
                description=(
                    "COUNT(DISTINCT user_id)\n"
                    "Counted over the acquisition population, before filtering "
                    "to purchasers, so users who never order are counted here."
                ),
            ),
        ],
    )


def _purchasing_customers_flow(
    suffix: str,
) -> tuple[list[TransformationNode], list[TransformationEdge]]:
    """Purchasing Customers: acquired users with at least one qualifying order."""
    nodes, edges = _acquisition_stage(suffix)
    nodes.append(
        TransformationNode(
            id=f"purch_cust_output{suffix}",
            label="Purchasing Customers",
            node_type=TransformationNodeType.OUTPUT,
            description=(
                "Acquired users with at least one order in their first six months."
            ),
            icon="output.png",
            x=5, y=0.6,
        )
    )
    edges.append(
        TransformationEdge(
            f"{_QUALIFYING_ID}{suffix}", f"purch_cust_output{suffix}",
            "Distinct Count",
            description=(
                "COUNT(DISTINCT user_id)\n"
                "Counted over the qualifying orders: a user counts once however "
                "many orders they placed."
            ),
        )
    )
    return nodes, edges


def _total_orders_flow(
    suffix: str,
) -> tuple[list[TransformationNode], list[TransformationEdge]]:
    """Total Orders: qualifying orders placed by the acquisition group."""
    nodes, edges = _acquisition_stage(suffix)
    nodes.append(
        TransformationNode(
            id=f"tot_orders_output{suffix}",
            label="Total Orders",
            node_type=TransformationNodeType.AGGREGATION,
            description=(
                "Orders placed by the acquisition group in their first six months."
            ),
            icon="output.png",
            x=5, y=0.6,
        )
    )
    edges.append(
        TransformationEdge(
            f"{_QUALIFYING_ID}{suffix}", f"tot_orders_output{suffix}",
            "Distinct Count",
            description=(
                "COUNT(DISTINCT order_id)\n"
                "Counted over the qualifying orders of the acquisition group."
            ),
        )
    )
    return nodes, edges


def _gross_value_flow() -> tuple[list[TransformationNode], list[TransformationEdge]]:
    """Total Gross Order Value: qualifying orders priced out line by line."""
    nodes, edges = _acquisition_stage("_gv")

    nodes += [
        # Source tables all sit in column 0; the lower chain then lines its
        # steps up with the upper one, so gross_value ends in the same column
        # as qualifying_orders and the join below them stays square.
        TransformationNode(
            id="raw_order_items_gv",
            label="raw_order_items",
            node_type=TransformationNodeType.SOURCE_TABLE,
            description="One row per order line.",
            icon="source_table.png",
            x=0, y=2.4,
        ),
        TransformationNode(
            id="raw_products_gv",
            label="raw_products",
            node_type=TransformationNodeType.SOURCE_TABLE,
            description="Product price and supply cost.",
            icon="source_table.png",
            x=0, y=3.6,
        ),
        TransformationNode(
            id="priced_lines_gv",
            label="priced_order_items",
            node_type=TransformationNodeType.JOIN,
            description="Order lines with their product's revenue and cost attached.",
            icon="join.png",
            x=3, y=3.0,
        ),
        TransformationNode(
            id="gross_value_gv",
            label="gross_value",
            node_type=TransformationNodeType.NEW_COLUMN,
            description="What an order line sold for, less what it cost to make.",
            icon="new_column.png",
            x=4, y=3.0,
        ),
        TransformationNode(
            id="qualifying_lines_gv",
            label="qualifying_order_lines",
            node_type=TransformationNodeType.JOIN,
            description="The order lines belonging to qualifying orders.",
            icon="join.png",
            x=5, y=1.8,
        ),
        TransformationNode(
            id="tot_gross_output_gv",
            label="Total Gross Order Value",
            node_type=TransformationNodeType.AGGREGATION,
            description=(
                "Value generated by the acquisition group in their first six months."
            ),
            icon="output.png",
            x=6, y=1.8,
        ),
    ]

    products_detail = (
        "FROM raw_order_items JOIN raw_products USING (product_id)\n"
        "Enriches each order line with the product's revenue and cost."
    )
    lines_detail = (
        "FROM qualifying_orders JOIN gross_value USING (order_id)\n"
        "Keeps only the lines belonging to orders inside each user's first "
        "six months."
    )

    edges += [
        TransformationEdge(
            "raw_order_items_gv", "priced_lines_gv", "Join",
            description=products_detail,
        ),
        TransformationEdge(
            "raw_products_gv", "priced_lines_gv", "Join",
            description=products_detail,
        ),
        TransformationEdge(
            "priced_lines_gv", "gross_value_gv", "New Column",
            description=(
                "SELECT (revenue - cost) AS gross_value\n"
                "Computed for each order line."
            ),
        ),
        TransformationEdge(
            f"{_QUALIFYING_ID}_gv", "qualifying_lines_gv", "Join",
            description=lines_detail,
        ),
        TransformationEdge(
            "gross_value_gv", "qualifying_lines_gv", "Join",
            description=lines_detail,
        ),
        TransformationEdge(
            "qualifying_lines_gv", "tot_gross_output_gv", "Sum",
            description=(
                "SUM(gross_value)\n"
                "Summed over every qualifying order line of the acquisition group."
            ),
        ),
    ]

    return nodes, edges


TRANSFORMATION_FLOWS: dict[
    str, tuple[list[TransformationNode], list[TransformationEdge]]
] = {
    "acq_users": _acquired_users_flow(),
    "purch_cust_1": _purchasing_customers_flow("_pc1"),
    "purch_cust_2": _purchasing_customers_flow("_pc2"),
    "tot_orders_1": _total_orders_flow("_to1"),
    "tot_orders_2": _total_orders_flow("_to2"),
    "tot_gross_val": _gross_value_flow(),
}
