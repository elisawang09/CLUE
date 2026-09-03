"""
Session-state plumbing for the simulator's scenario controls.

Each factor moves on its own: the scenario KPI is computed from whatever the
three assumptions say and then compared against the goal, so a scenario is free
to land above or below it. Nothing here writes back to the historical baseline.
"""

from __future__ import annotations

import streamlit as st

from data.metrics import BaselineMetrics
from data.scenario import DEFAULT_UPLIFT_PERCENT, Scenario, from_baseline

# Session keys for the three assumptions and the planning goal.
CONVERSION_KEY = "sim_conversion"
ORDERS_KEY = "sim_orders_per_cust"
ORDER_VALUE_KEY = "sim_order_value"
UPLIFT_KEY = "sim_uplift"
UPLIFT_INPUT_KEY = "sim_uplift_input"

# Goal stepper bounds, in percent above the historical baseline.
UPLIFT_MIN, UPLIFT_MAX, UPLIFT_STEP = 0, 100, 5


def slider_bounds(baseline: BaselineMetrics) -> dict[str, tuple[float, float, float]]:
    """
    (min, max, step) per factor, scaled to the observed values.

    Room to move in both directions -- twice the baseline at the top -- rather
    than a fixed range, which cannot fit factors as different in scale as a
    conversion rate and an order count. The conversion rate is held in
    percentage points so the slider labels itself in the units the metric is
    read in.
    """
    return {
        CONVERSION_KEY: (0.0, 100.0, 0.5),
        ORDERS_KEY: (
            0.0,
            round(baseline.orders_per_purchasing_customer * 2, 1),
            0.1,
        ),
        ORDER_VALUE_KEY: (
            0.0,
            round(baseline.average_order_value * 2, 2),
            0.01,
        ),
    }


def initialize_scenario_state(baseline: BaselineMetrics) -> None:
    """Seed the controls at the historical baseline, on first render only."""
    defaults = {
        CONVERSION_KEY: float(baseline.conversion_rate) * 100,
        ORDERS_KEY: float(baseline.orders_per_purchasing_customer),
        ORDER_VALUE_KEY: float(baseline.average_order_value),
        UPLIFT_KEY: DEFAULT_UPLIFT_PERCENT,
        UPLIFT_INPUT_KEY: DEFAULT_UPLIFT_PERCENT,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def current_scenario(baseline: BaselineMetrics) -> Scenario:
    """The scenario the controls currently describe."""
    if CONVERSION_KEY not in st.session_state:
        return from_baseline(baseline)
    return Scenario(
        conversion_rate=float(st.session_state[CONVERSION_KEY]) / 100,
        orders_per_purchasing_customer=float(st.session_state[ORDERS_KEY]),
        average_order_value=float(st.session_state[ORDER_VALUE_KEY]),
        acquired_users=baseline.acquired_users,
    )


def uplift_percent() -> float:
    """Planning goal, as a percentage above the historical baseline."""
    return float(st.session_state.get(UPLIFT_KEY, DEFAULT_UPLIFT_PERCENT))
