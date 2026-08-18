"""
registry.py
-----------
What each metric is called, what it means, and how it is calculated.

Names follow the observation-window filter, so a 9-month window really does say
"9-Month Customer Value" everywhere rather than displaying a stale "6-Month"
label over different numbers.

Calculation expressions are stored as tokens rather than prose so the panel can
render referenced metrics as links, letting someone step into a component
definition one metric at a time. Nothing here draws a dependency tree -- this
is a conventional dashboard, and the metric-at-a-time constraint is the point.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from metrics.compute import CohortMetrics

# Grain of the rows behind a metric, which decides what "View Underlying Data"
# shows: one row per acquired user, or one row per order line.
CUSTOMER_GRAIN = "customer"
ORDER_ITEM_GRAIN = "order_item"


@dataclass(frozen=True)
class Token:
    """A fragment of a calculation expression; `ref` makes it a link."""

    text: str
    ref: str | None = None


@dataclass(frozen=True)
class MetricDef:
    id: str
    name: Callable[[CohortMetrics], str]
    description: Callable[[CohortMetrics], str]
    expression: Callable[[CohortMetrics], list[Token]]
    value: Callable[[CohortMetrics], float | int | None]
    fmt: Callable[[float | int], str]
    grain: str
    unit: str = ""
    source: str = "Customer Analytics Model"
    is_card: bool = False
    notes: Callable[[CohortMetrics], str] = field(default=lambda m: "")

    # Name of the corresponding metric in CLUE, or None when it has no
    # counterpart there yet. Only metrics with one offer an "Open in CLUE"
    # menu item, so extending the handoff to another card is a one-line change.
    #
    # NOTE: CLUE is still built around PLTV, whose components differ from this
    # dashboard's. Realigning it is separate follow-up work; until then this
    # mapping hands over to a related but not identical metric.
    clue_metric: str | None = None


def money(value: float) -> str:
    return f"${value:,.2f}" if abs(value) < 1000 else f"${value:,.0f}"


def whole_money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1%}"


def count(value: float) -> str:
    return f"{value:,.0f}"


def decimal(value: float) -> str:
    return f"{value:,.1f}"


METRICS: dict[str, MetricDef] = {}


def _register(metric: MetricDef) -> MetricDef:
    METRICS[metric.id] = metric
    return metric


# ---------------------------------------------------------------------------
# Primary metric
# ---------------------------------------------------------------------------

_register(
    MetricDef(
        id="customer_value",
        name=lambda m: f"{m.window_label} Customer Value",
        description=lambda m: (
            f"Average value generated per acquired user during the first "
            f"{m.cohort.window} months after acquisition. Every user acquired in "
            f"the reference period counts toward the average, including those who "
            f"never placed an order."
        ),
        expression=lambda m: [
            Token(f"{m.window_label} Purchase Conversion Rate", "conversion_rate"),
            Token("×"),
            Token("Orders per Purchasing Customer", "orders_per_purchasing_customer"),
            Token("×"),
            Token("Average Order Value", "average_order_value"),
        ],
        value=lambda m: m.customer_value,
        fmt=money,
        grain=CUSTOMER_GRAIN,
        unit="per acquired user",
        is_card=True,
        clue_metric="PLTV",
        notes=lambda m: (
            f"Equivalently: Total Gross Order Value ÷ Acquired Users = "
            f"{money(m.total_gross_order_value)} ÷ {count(m.acquired_users)}."
        ),
    )
)

# ---------------------------------------------------------------------------
# Supporting cards
# ---------------------------------------------------------------------------

_register(
    MetricDef(
        id="conversion_rate",
        name=lambda m: f"{m.window_label} Purchase Conversion Rate",
        description=lambda m: (
            f"Percentage of acquired users who place at least one order during "
            f"their first {m.cohort.window} months after acquisition."
        ),
        expression=lambda m: [
            Token("Purchasing Customers", "purchasing_customers"),
            Token("÷"),
            Token("Acquired Users", "acquired_users"),
        ],
        value=lambda m: m.conversion_rate,
        fmt=percent,
        grain=CUSTOMER_GRAIN,
        is_card=True,
    )
)

_register(
    MetricDef(
        id="orders_per_purchasing_customer",
        name=lambda m: "Orders per Purchasing Customer",
        description=lambda m: (
            f"Average number of orders placed by a customer who ordered at least "
            f"once in their first {m.cohort.window} months. Users who never "
            f"ordered are excluded from this average."
        ),
        expression=lambda m: [
            Token("Total Orders", "total_orders"),
            Token("÷"),
            Token("Purchasing Customers", "purchasing_customers"),
        ],
        value=lambda m: m.orders_per_purchasing_customer,
        fmt=decimal,
        grain=CUSTOMER_GRAIN,
        is_card=True,
    )
)

_register(
    MetricDef(
        id="average_order_value",
        name=lambda m: "Average Order Value",
        description=lambda m: (
            "Average gross value of a single qualifying order -- what the order "
            "was worth after the cost of the items in it."
        ),
        expression=lambda m: [
            Token("Total Gross Order Value", "total_gross_order_value"),
            Token("÷"),
            Token("Total Orders", "total_orders"),
        ],
        value=lambda m: m.average_order_value,
        fmt=money,
        grain=ORDER_ITEM_GRAIN,
        is_card=True,
    )
)

_register(
    MetricDef(
        id="acquired_users",
        name=lambda m: "Acquired Users",
        description=lambda m: (
            "Number of users whose account was created during the reference "
            "acquisition period, whether or not they went on to order."
        ),
        expression=lambda m: [
            Token("COUNT(DISTINCT user_id) where acquisition date falls in "),
            Token(m.cohort.label),
        ],
        value=lambda m: m.acquired_users,
        fmt=count,
        grain=CUSTOMER_GRAIN,
        is_card=True,
    )
)

# ---------------------------------------------------------------------------
# Component metrics, reachable by drilling into an expression
# ---------------------------------------------------------------------------

_register(
    MetricDef(
        id="purchasing_customers",
        name=lambda m: "Purchasing Customers",
        description=lambda m: (
            f"Acquired users who placed at least one order within their first "
            f"{m.cohort.window} months."
        ),
        expression=lambda m: [
            Token(
                f"COUNT(DISTINCT user_id) with ≥1 order in their first "
                f"{m.cohort.window} months"
            )
        ],
        value=lambda m: m.purchasing_customers,
        fmt=count,
        grain=CUSTOMER_GRAIN,
    )
)

_register(
    MetricDef(
        id="total_orders",
        name=lambda m: "Total Orders",
        description=lambda m: (
            f"Orders placed by users acquired in the reference period, counting "
            f"only orders within each user's first {m.cohort.window} months."
        ),
        expression=lambda m: [Token("COUNT(DISTINCT order_id) for qualifying orders")],
        value=lambda m: m.total_orders,
        fmt=count,
        grain=ORDER_ITEM_GRAIN,
    )
)

_register(
    MetricDef(
        id="total_gross_order_value",
        name=lambda m: "Total Gross Order Value",
        description=lambda m: (
            "Total value of all qualifying orders, summed across every order line."
        ),
        expression=lambda m: [
            Token("SUM("),
            Token("gross_value", "gross_value"),
            Token(") for qualifying orders"),
        ],
        value=lambda m: m.total_gross_order_value,
        fmt=whole_money,
        grain=ORDER_ITEM_GRAIN,
    )
)

_register(
    MetricDef(
        id="gross_value",
        name=lambda m: "gross_value",
        description=lambda m: (
            "A field on each order line: what the item sold for, less what it "
            "cost to make. Revenue is the product's price; cost is the sum of "
            "its supply components."
        ),
        expression=lambda m: [Token("revenue − cost")],
        value=lambda m: None,
        fmt=money,
        grain=ORDER_ITEM_GRAIN,
        source="Customer Analytics Model · order line field",
    )
)


CARD_IDS: tuple[str, ...] = tuple(
    metric_id for metric_id, metric in METRICS.items() if metric.is_card
)

PRIMARY_ID = "customer_value"


def formatted_value(metric_id: str, metrics: CohortMetrics) -> str:
    """Display string for a metric, or an em dash when it has no single value."""
    metric = METRICS[metric_id]
    value = metric.value(metrics)
    if value is None:
        return "—"
    try:
        if value != value:  # NaN
            return "—"
    except TypeError:
        return "—"
    return metric.fmt(value)
