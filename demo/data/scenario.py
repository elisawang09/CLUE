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
    90-Day Customer Value   = Conversion x Orders per Customer x AOV

The assumptions are taken exactly as set. Nothing here widens them into a
range, and nothing generates alternative scenarios on the participant's behalf:
a tolerance band would be *our* guess at what counts as a plausible movement,
and the point of the simulator is to let someone explore a movement we have not
anticipated -- a campaign that beats anything in the history, for instance.

`acquired_users` is the *future* acquisition volume, not the size of the cohort
being explained. It scales the absolute counts a scenario implies and does not
affect the headline at all: customer value is per acquired user, so it divides
back out. Holding it the same across scenarios is what makes their counts
comparable.
"""

from __future__ import annotations

from dataclasses import dataclass

from data.metrics import BaselineMetrics

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
    """
    The scenario that reproduces history: every assumption at its observed
    value, applied to the future acquisition volume.

    This is the comparison column on every pathway card -- "what the next three
    months would look like if nothing changed" -- so it has to be built on the
    same acquired-user count as the scenarios it is compared against.
    """
    return Scenario(
        conversion_rate=baseline.conversion_rate,
        orders_per_purchasing_customer=baseline.orders_per_purchasing_customer,
        average_order_value=baseline.average_order_value,
        acquired_users=baseline.future_acquired_users,
    )


def from_observed_best(baseline: BaselineMetrics) -> Scenario:
    """
    Each factor at its best month in the reference period.

    Offered as a starting point for someone facing three sliders and no obvious
    place to begin. It is a *composite* -- the three maxima can come from three
    different months -- so the card that shows it says so rather than letting it
    read as a quarter that actually happened.
    """
    conversion, orders, order_value = baseline.observed_best
    return Scenario(
        conversion_rate=conversion,
        orders_per_purchasing_customer=orders,
        average_order_value=order_value,
        acquired_users=baseline.future_acquired_users,
    )


def goal_value(baseline: BaselineMetrics, uplift_percent: float) -> float:
    """
    The planning goal: what users acquired over the next 3 months should
    generate during their first 90 days, relative to the reference cohort.
    """
    return baseline.customer_value * (1 + uplift_percent / 100)


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
