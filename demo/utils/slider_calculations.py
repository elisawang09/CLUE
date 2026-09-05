"""
Session-state plumbing for the simulator's scenario controls.

Each factor moves on its own: the scenario KPI is computed from whatever the
three assumptions say and then compared against the goal, so a scenario is free
to land above or below it. Nothing here writes back to the historical baseline.

Pinned scenarios are snapshots. Pinning does not move the sliders -- the next
scenario is usually a variation on the last one, so the controls stay where
they were and the participant adjusts from there.
"""

from __future__ import annotations

import streamlit as st

from data.metrics import BaselineMetrics
from data.scenario import DEFAULT_UPLIFT_PERCENT, Scenario, from_baseline

# Pinned pathway cards, and which card the simulation runs on.
PINNED_KEY = "sim_pinned_scenarios"
SELECTED_KEY = "sim_selected_scenario"

# Slots in the scenario list, counting the "Best observed" starting point --
# so dismissing that frees room for one more pinned scenario. Six rows sit in
# view without scrolling, which is the number the panel can actually be
# compared across at a glance.
MAX_RAIL_CARDS = 6

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
        # The scenario describes the *next* three months, so it is propagated
        # against the future acquisition volume, not the size of the cohort
        # being explained.
        acquired_users=baseline.future_acquired_users,
    )


def uplift_percent() -> float:
    """Planning goal, as a percentage above the historical baseline."""
    return float(st.session_state.get(UPLIFT_KEY, DEFAULT_UPLIFT_PERCENT))


# ---------------------------------------------------------------------------
# Pinned pathway cards
# ---------------------------------------------------------------------------

def pinned_scenarios() -> list[tuple[str, Scenario]]:
    """(name, scenario) for each pinned card, in the order they were pinned."""
    return list(st.session_state.get(PINNED_KEY, []))


def next_scenario_name() -> str:
    """
    A, B, C ... for the next pinned card.

    Named automatically rather than by the participant: each card already lists
    its three assumptions, which is what distinguishes it, and a naming step
    would interrupt the exploration it is meant to support.
    """
    return chr(ord("A") + len(pinned_scenarios()))


def can_pin(other_cards: int = 0) -> bool:
    """
    Whether the rail has room for another card.

    `other_cards` is how many slots are already taken by cards that are not
    pinned scenarios -- today just the "Best observed" starting point, when it
    has not been dismissed.
    """
    return len(pinned_scenarios()) + other_cards < MAX_RAIL_CARDS


def pin_scenario(scenario: Scenario, other_cards: int = 0) -> None:
    """Freeze the current assumptions as a card. The sliders do not move."""
    if not can_pin(other_cards):
        return
    st.session_state.setdefault(PINNED_KEY, [])
    st.session_state[PINNED_KEY].append((next_scenario_name(), scenario))


def remove_pinned(name: str) -> None:
    """Drop one card, and fall back to the live one if it was selected."""
    st.session_state[PINNED_KEY] = [
        (pinned_name, scenario)
        for pinned_name, scenario in pinned_scenarios()
        if pinned_name != name
    ]
    if st.session_state.get(SELECTED_KEY) == name:
        st.session_state[SELECTED_KEY] = CURRENT_CARD_ID


# Identifier of the live card, which always exists and cannot be removed.
CURRENT_CARD_ID = "__current__"


def selected_card_id() -> str:
    return st.session_state.get(SELECTED_KEY, CURRENT_CARD_ID)


def select_card(card_id: str) -> None:
    st.session_state[SELECTED_KEY] = card_id
