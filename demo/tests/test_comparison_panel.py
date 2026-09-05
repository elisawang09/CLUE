"""
Tests for the scenario comparison rail: pinning, selection, and removal.

The panel generates nothing on the participant's behalf, so what is worth
pinning down is the bookkeeping -- that a pinned card keeps the assumptions it
was pinned with, that the sliders do not move underneath it, and that removing
the selected card leaves the simulator with something to simulate.
"""

import unittest

import streamlit as st

from components.styles import (
    result_block_html,
    scenario_rail_css,
    scenario_row_html,
)
from data.metrics import compute_baseline
from data.scenario import Scenario, from_baseline
from utils.slider_calculations import (
    CONVERSION_KEY,
    CURRENT_CARD_ID,
    MAX_RAIL_CARDS,
    ORDER_VALUE_KEY,
    ORDERS_KEY,
    PINNED_KEY,
    SELECTED_KEY,
    can_pin,
    next_scenario_name,
    pin_scenario,
    pinned_scenarios,
    remove_pinned,
    select_card,
    selected_card_id,
)


class TestPinning(unittest.TestCase):
    def setUp(self):
        for key in (PINNED_KEY, SELECTED_KEY, CONVERSION_KEY, ORDERS_KEY,
                    ORDER_VALUE_KEY):
            st.session_state.pop(key, None)
        self.baseline = compute_baseline()

    def scenario(self, conversion: float) -> Scenario:
        return Scenario(
            conversion_rate=conversion,
            orders_per_purchasing_customer=(
                self.baseline.orders_per_purchasing_customer
            ),
            average_order_value=self.baseline.average_order_value,
            acquired_users=self.baseline.future_acquired_users,
        )

    def test_cards_are_named_automatically_in_order(self):
        self.assertEqual(next_scenario_name(), "A")
        pin_scenario(self.scenario(0.41))
        self.assertEqual(next_scenario_name(), "B")
        pin_scenario(self.scenario(0.38))
        self.assertEqual([name for name, _ in pinned_scenarios()], ["A", "B"])

    def test_a_pinned_card_keeps_the_assumptions_it_was_pinned_with(self):
        """A snapshot, not a live view: later slider moves must not reach it."""
        pin_scenario(self.scenario(0.41))
        st.session_state[CONVERSION_KEY] = 99.0
        _, pinned = pinned_scenarios()[0]
        self.assertAlmostEqual(pinned.conversion_rate, 0.41)

    def test_pinning_does_not_move_the_sliders(self):
        st.session_state[CONVERSION_KEY] = 41.0
        pin_scenario(self.scenario(0.41))
        self.assertEqual(st.session_state[CONVERSION_KEY], 41.0)

    def test_the_rail_is_capped(self):
        for index in range(MAX_RAIL_CARDS):
            self.assertTrue(can_pin(), f"blocked early at {index}")
            pin_scenario(self.scenario(0.3 + index / 100))
        self.assertFalse(can_pin())
        pin_scenario(self.scenario(0.99))
        self.assertEqual(len(pinned_scenarios()), MAX_RAIL_CARDS)

    def test_the_cap_counts_every_slot_on_the_rail(self):
        """
        The "Best observed" card occupies a slot. Dismissing it frees room for
        one more pinned scenario rather than leaving a gap.
        """
        for index in range(MAX_RAIL_CARDS - 1):
            pin_scenario(self.scenario(0.3 + index / 100), other_cards=1)
        self.assertFalse(can_pin(other_cards=1), "reference card not counted")
        self.assertTrue(can_pin(other_cards=0), "slot not freed once dismissed")

    def test_removing_a_card_drops_only_that_one(self):
        pin_scenario(self.scenario(0.41))
        pin_scenario(self.scenario(0.38))
        remove_pinned("A")
        self.assertEqual([name for name, _ in pinned_scenarios()], ["B"])

    def test_removing_the_selected_card_falls_back_to_the_live_one(self):
        """Otherwise the simulator would be pointed at a card that is gone."""
        pin_scenario(self.scenario(0.41))
        select_card("A")
        self.assertEqual(selected_card_id(), "A")
        remove_pinned("A")
        self.assertEqual(selected_card_id(), CURRENT_CARD_ID)

    def test_the_live_scenario_is_the_default_target(self):
        """
        The live scenario is not a card any more -- it lives beside the sliders
        -- so with nothing selected the simulation still has something to run.
        """
        self.assertEqual(selected_card_id(), CURRENT_CARD_ID)


class TestRowMarkup(unittest.TestCase):
    """
    The whole list is one st.markdown call per row, and markdown reads any line
    starting with four spaces as an indented code block. A pretty-printed row
    would render as literal HTML text.
    """

    def row(self, **overrides) -> str:
        defaults = dict(
            title="Scenario A",
            note="pinned",
            headline="$123.76",
            assumptions="41.0% · 35.2 · $8.58",
            goal_met=True,
            goal_text="✓ meets goal",
            is_selected=False,
        )
        defaults.update(overrides)
        return scenario_row_html(**defaults)

    def test_a_row_is_a_single_line(self):
        self.assertNotIn("\n", self.row())

    def test_no_line_of_the_list_would_read_as_a_code_block(self):
        markup = (
            scenario_rail_css()
            + self.row()
            + self.row(title="Scenario B")
            + self.row(title="Scenario C")
        )
        indented = [
            line
            for line in markup.splitlines()
            if line.strip() and len(line) - len(line.lstrip()) >= 4
        ]
        self.assertEqual(indented, [], "markdown would render these literally")

    def test_a_row_carries_what_tells_scenarios_apart(self):
        html = self.row(is_selected=True)
        self.assertIn("clue-lite is-selected", html)
        self.assertIn("Scenario A", html)
        self.assertIn("$123.76", html)
        self.assertIn("41.0% · 35.2 · $8.58", html)
        self.assertIn("clue-goal met", html)

    def test_a_row_leaves_the_implied_pathway_to_the_results_panel(self):
        """Dropping it is what lets six rows sit in view instead of two."""
        html = self.row()
        for label in ("Purchasing", "Total Orders", "Gross value", "Future users"):
            self.assertNotIn(label, html)

    def test_a_missed_goal_gets_the_other_state(self):
        html = self.row(goal_met=False, goal_text="below goal")
        self.assertIn("clue-goal missed", html)

    def test_the_style_block_is_balanced(self):
        css = scenario_rail_css()
        self.assertEqual(css.count("{"), css.count("}"))
        self.assertIn(".clue-lite", css)

    def test_button_rules_do_not_use_a_child_selector(self):
        """
        The remove button carries a `help`, and Streamlit wraps a helped button
        in a tooltip target -- so the button is a grandchild. A child selector
        matches nothing, and a default white button covers the row while the
        positioning rules still apply.
        """
        css = scenario_rail_css()
        rules = [
            line for line in css.splitlines()
            if line.startswith(("[class*=", ".st-key-"))
        ]
        offenders = [line for line in rules if "div.stButton > button" in line]
        self.assertEqual(offenders, [], "child selector misses helped buttons")

    def test_the_select_overlay_stretches_to_the_whole_row(self):
        css = scenario_rail_css()
        block = css[css.index('[class*="st-key-select_"],'):]
        block = block[: block.index("}")]
        self.assertIn('[class*="st-key-select_"] div', block)
        self.assertIn('[class*="st-key-select_"] button', block)
        self.assertIn("height: 100% !important", block)
        self.assertIn("background: transparent !important", block)

    def test_the_remove_button_is_a_small_circle(self):
        css = scenario_rail_css()
        block = css[css.index('[class*="st-key-remove_"] button,'):]
        block = block[: block.index("}")]
        self.assertIn("border-radius: 50% !important", block)
        self.assertIn("height: 20px !important", block)
        self.assertIn("background: rgba(0, 0, 0, 0.3) !important", block)

    def test_the_list_column_keeps_the_card_width(self):
        """
        The rows got shorter, not narrower -- the left column is the width a
        card had on the old horizontal rail.
        """
        css = scenario_rail_css()
        block = css[css.index('.st-key-sim_split [data-testid="stColumn"]:first-child'):]
        block = block[: block.index("}")]
        self.assertIn("250px", block)

    def test_the_list_leaves_room_below_the_last_row(self):
        """
        The last row's border otherwise sits exactly on the scroll container's
        clip edge and loses its bottom line.
        """
        css = scenario_rail_css()
        block = css[css.index(".st-key-scenario_list {"):]
        block = block[: block.index("}")]
        padding = [
            line for line in block.splitlines() if line.startswith("padding:")
        ]
        self.assertTrue(padding, "no padding declared on the list")
        bottom = int(padding[0].split()[3].rstrip("px;"))
        self.assertGreaterEqual(bottom, 12)

    def test_the_result_blocks_are_reset_out_of_the_split_rules(self):
        """
        The split's column rules are descendant selectors, so they also match
        the three result columns nested inside it -- the first block inherited
        the scenario list's fixed 250px and its right-hand rule, and the last
        inherited flex-grow. One narrow block, one wide one, a stray line.
        """
        css = scenario_rail_css()
        block = css[css.index('.st-key-result_blocks [data-testid="stColumn"] {'):]
        block = block[: block.index("}")]
        self.assertIn("flex: 1 1 0 !important", block)
        self.assertIn("border-right: none !important", block)
        self.assertIn("padding-right: 0 !important", block)

    def test_the_result_blocks_are_stretched_to_equal_height(self):
        css = scenario_rail_css()
        row = css[css.index('.st-key-result_blocks [data-testid="stHorizontalBlock"]'):]
        row = row[: row.index("}")]
        self.assertIn("align-items: stretch !important", row)

        block = css[css.index(".clue-result-block {"):]
        block = block[: block.index("}")]
        self.assertIn("height: 100%", block)

    def test_a_result_block_is_one_element(self):
        """
        Heading and box together: with the heading as a separate Streamlit
        element the box has nothing definite to fill, and the three end at
        whatever height their own bullets reach.
        """
        html = result_block_html("Scenario result", "- one\n- two")
        self.assertNotIn("\n", html)
        self.assertIn("clue-result-title", html)
        self.assertIn("clue-detail-box", html)
        self.assertEqual(html.count("<li>"), 2)

    def test_a_rule_separates_the_two_columns(self):
        css = scenario_rail_css()
        block = css[css.index('.st-key-sim_split [data-testid="stColumn"]:first-child'):]
        block = block[: block.index("}")]
        self.assertIn("border-right:", block)



class TestComparisonBasis(unittest.TestCase):
    """Every card must be readable against the same denominator."""

    def setUp(self):
        self.baseline = compute_baseline()

    def test_the_before_column_uses_the_future_cohort(self):
        before = from_baseline(self.baseline)
        self.assertEqual(
            before.acquired_users, self.baseline.future_acquired_users
        )

    def test_before_and_after_share_a_cohort_size(self):
        before = from_baseline(self.baseline)
        after = Scenario(
            conversion_rate=0.41,
            orders_per_purchasing_customer=(
                self.baseline.orders_per_purchasing_customer
            ),
            average_order_value=self.baseline.average_order_value,
            acquired_users=self.baseline.future_acquired_users,
        )
        self.assertEqual(before.acquired_users, after.acquired_users)


if __name__ == "__main__":
    unittest.main()


class TestPropagationGraphCache(unittest.TestCase):
    """
    Selecting a scenario is now the whole interaction, so the graph is rebuilt
    far more often than when it sat behind a Simulate button.
    """

    def setUp(self):
        from components import simulation_result_graph as graph

        self.graph = graph
        for key in list(st.session_state.keys()):
            if str(key).startswith("sim_graph"):
                st.session_state.pop(key, None)
        self.baseline = compute_baseline()

    def deltas_for(self, conversion: float):
        from data.graph_data import simulation_deltas

        scenario = Scenario(
            conversion_rate=conversion,
            orders_per_purchasing_customer=(
                self.baseline.orders_per_purchasing_customer
            ),
            average_order_value=self.baseline.average_order_value,
            acquired_users=self.baseline.future_acquired_users,
        )
        return simulation_deltas(self.baseline, scenario)

    def test_different_scenarios_get_different_signatures(self):
        """
        The signature is the component key. A fixed key with changing state
        leaves the previously mounted graph on screen -- which nobody noticed
        while simulating was a button press, and everybody would notice now.
        """
        first = self.graph._signature(self.deltas_for(0.41))
        second = self.graph._signature(self.deltas_for(0.38))
        self.assertNotEqual(first, second)

    def test_the_same_scenario_gets_a_stable_signature(self):
        self.assertEqual(
            self.graph._signature(self.deltas_for(0.41)),
            self.graph._signature(self.deltas_for(0.41)),
        )

    def test_a_state_is_built_once_per_scenario(self):
        deltas = self.deltas_for(0.41)
        signature = self.graph._signature(deltas)
        first = self.graph._cached_state(signature, deltas)
        second = self.graph._cached_state(signature, deltas)
        self.assertIs(first, second)

    def test_the_cache_is_bounded(self):
        """
        Without eviction a session accumulates one flow state per set of
        assumptions ever looked at -- including every step of a slider drag.
        """
        for step in range(self.graph._MAX_CACHED_GRAPHS + 4):
            deltas = self.deltas_for(0.30 + step / 100)
            self.graph._cached_state(self.graph._signature(deltas), deltas)

        cached = [k for k in st.session_state.keys()
                  if str(k).startswith(f"{self.graph._SIM_GRAPH_KEY}_")]
        self.assertLessEqual(len(cached), self.graph._MAX_CACHED_GRAPHS)
