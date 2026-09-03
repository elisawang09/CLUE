"""
scenario.py
-----------
Hypothetical scenario state for the simulator, kept apart from observed history.

The historical baseline answers "what happened for the reference acquisition
group?"; a scenario answers "what would the metric become if these assumptions
held for the future acquisition group?". Nothing here modifies a
BaselineMetrics -- data/metrics.py stays the only source of observed values, so
changing an assumption can never disturb the numbers the rest of CLUE shows.

A scenario is three assumptions; everything downstream is propagated from them:

    Purchasing Customers    = Acquired Users x Conversion Rate
    Total Orders            = Purchasing Customers x Orders per Customer
    Total Gross Order Value = Total Orders x Average Order Value
    6-Month Customer Value  = Conversion x Orders per Customer x AOV
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from data.metrics import BaselineMetrics, decimal, money, percent

# Default planning goal, as a percentage above the historical baseline.
DEFAULT_UPLIFT_PERCENT = 15


@dataclass(frozen=True)
class Scenario:
    """
    One set of assumptions about the future acquisition group.

    Propagated counts stay exact rather than being rounded to whole customers
    and orders; rounding happens when they are formatted for display, so the
    identities between them hold exactly at every step.
    """

    conversion_rate: float
    orders_per_purchasing_customer: float
    average_order_value: float
    acquired_users: int

    # -- propagated quantities ------------------------------------------------

    @property
    def purchasing_customers(self) -> float:
        return self.acquired_users * self.conversion_rate

    @property
    def total_orders(self) -> float:
        return self.purchasing_customers * self.orders_per_purchasing_customer

    @property
    def total_gross_order_value(self) -> float:
        return self.total_orders * self.average_order_value

    @property
    def customer_value(self) -> float:
        return (
            self.conversion_rate
            * self.orders_per_purchasing_customer
            * self.average_order_value
        )


def from_baseline(baseline: BaselineMetrics) -> Scenario:
    """The scenario that reproduces history: every assumption at its observed value."""
    return Scenario(
        conversion_rate=baseline.conversion_rate,
        orders_per_purchasing_customer=baseline.orders_per_purchasing_customer,
        average_order_value=baseline.average_order_value,
        acquired_users=baseline.acquired_users,
    )


def goal_value(baseline: BaselineMetrics, uplift_percent: float) -> float:
    """
    The planning goal: what users acquired over the next 3 months should
    generate during their first 6 months, relative to the reference group.
    """
    return baseline.customer_value * (1 + uplift_percent / 100)


# ---------------------------------------------------------------------------
# Scenario starters
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Starter:
    """
    A hypothetical starting point for exploration -- not a recommendation.

    Starters are returned in a fixed order and carry no score: CLUE has not
    established that any of them is achievable, preferable, or best.
    """

    key: str
    name: str
    summary: str
    scenario: Scenario


def starters(current: Scenario, goal: float) -> list[Starter]:
    """
    Three starting points, each closing the gap to the goal through a different
    factor while holding the other two where they are.

    They start from the scenario currently set in the controls, not from the
    historical baseline: after moving a slider, the starters answer "from here,
    what single change would reach the goal?".
    """
    base = current
    factor = goal / current.customer_value if current.customer_value else 1.0

    def _summary(label: str, before: str, after: str) -> str:
        return f"{label}: {before} → {after}, other factors held where they are"

    conversion = min(1.0, base.conversion_rate * factor)
    orders = base.orders_per_purchasing_customer * factor
    order_value = base.average_order_value * factor

    return [
        Starter(
            key="conversion",
            name="Conversion-led",
            summary=_summary(
                "6-Month Purchase Conversion Rate",
                percent(base.conversion_rate),
                percent(conversion),
            ),
            scenario=replace(base, conversion_rate=conversion),
        ),
        Starter(
            key="frequency",
            name="Frequency-led",
            summary=_summary(
                "Orders per Purchasing Customer",
                decimal(base.orders_per_purchasing_customer),
                decimal(orders),
            ),
            scenario=replace(base, orders_per_purchasing_customer=orders),
        ),
        Starter(
            key="order_value",
            name="Order-value-led",
            summary=_summary(
                "Average Order Value",
                money(base.average_order_value),
                money(order_value),
            ),
            scenario=replace(base, average_order_value=order_value),
        ),
    ]


def combine(current: Scenario, chosen: list[Starter]) -> Scenario:
    """
    One scenario from several starters.

    Each starter moves a single factor, so selecting more than one simply
    carries each of those assumptions into the same scenario, on top of
    whatever the controls currently say. Selecting none changes nothing.
    """
    base = current
    changes: dict[str, float] = {}
    for starter in chosen:
        if starter.key == "conversion":
            changes["conversion_rate"] = starter.scenario.conversion_rate
        elif starter.key == "frequency":
            changes["orders_per_purchasing_customer"] = (
                starter.scenario.orders_per_purchasing_customer
            )
        elif starter.key == "order_value":
            changes["average_order_value"] = starter.scenario.average_order_value
    return replace(base, **changes)


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------

TOLERANCE = 1e-3


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE + TOLERANCE * abs(b)


def run_scenario_checks(scenario: Scenario) -> list[tuple[str, bool, str]]:
    """
    The spec's scenario-side assertions.

    Propagation is computed rather than stored, so these hold by construction;
    they exist to catch a future change that breaks that.
    """
    return [
        (
            "Scenario value == conversion x orders per customer x AOV",
            _close(
                scenario.customer_value,
                scenario.conversion_rate
                * scenario.orders_per_purchasing_customer
                * scenario.average_order_value,
            ),
            f"{scenario.customer_value:.6f}",
        ),
        (
            "Purchasing Customers == acquired users x conversion rate",
            _close(
                scenario.purchasing_customers,
                scenario.acquired_users * scenario.conversion_rate,
            ),
            f"{scenario.purchasing_customers:.6f}",
        ),
        (
            "Total Orders == purchasing customers x orders per customer",
            _close(
                scenario.total_orders,
                scenario.purchasing_customers
                * scenario.orders_per_purchasing_customer,
            ),
            f"{scenario.total_orders:.6f}",
        ),
        (
            "Total Gross Order Value == total orders x AOV",
            _close(
                scenario.total_gross_order_value,
                scenario.total_orders * scenario.average_order_value,
            ),
            f"{scenario.total_gross_order_value:.6f}",
        ),
    ]
