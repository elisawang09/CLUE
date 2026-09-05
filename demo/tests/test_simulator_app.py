"""
The simulator driven end to end through Streamlit's AppTest.

These cover the wiring the unit tests cannot: that the live scenario appears
beside the sliders rather than in the list, that clicking a row selects it and
brings up its results, and that with nothing selected the results panel says so
instead of propagating a scenario nobody chose.
"""

import re
import unittest
from pathlib import Path

APP = str(Path(__file__).resolve().parent.parent / "main.py")


def markdown_text(app) -> str:
    return " ".join(block.value for block in app.markdown)


def list_html(app) -> str:
    """
    Just the rendered scenario rows.

    Not the whole page: the injected <style> block names every class it styles,
    so counting class names across all markdown counts the CSS rule as well as
    the row that uses it.
    """
    return " ".join(
        block.value
        for block in app.markdown
        if block.value.startswith('<div class="clue-lite')
    )


def row_names(app) -> list[str]:
    return re.findall(r'clue-lite-name">([^<]*)', list_html(app))


def selected_count(app) -> int:
    return list_html(app).count("clue-lite is-selected")


def shows_hint(app) -> bool:
    return any(
        block.value.startswith('<div class="clue-hint"') for block in app.markdown
    )


def strip_head(app) -> str:
    """
    The left end of the scenario band: the headline and its comparison.

    Matched on the rendered tag, not the bare class name -- the injected
    <style> block names every class it styles, so `"clue-strip-value" in
    block.value` finds the stylesheet first and returns markup with no numbers
    in it.
    """
    for block in app.markdown:
        if 'clue-strip-value">' in block.value:
            return block.value
    return ""


def strip_stats(app) -> str:
    """The middle of the band: the implied data changes, laid out wide."""
    for block in app.markdown:
        if block.value.startswith('<div class="clue-strip-stats"'):
            return block.value
    return ""


def results_heading(app) -> str:
    for block in app.markdown:
        if block.value.startswith("###### Simulation Results"):
            return block.value
    return ""


class TestSimulatorPanels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")
        cls.AppTest = AppTest

    def open_simulator(self):
        app = self.AppTest.from_file(APP, default_timeout=300)
        app.query_params["start"] = "2024-01"
        app.query_params["end"] = "2024-06"
        app.run()
        app.button(key="view_switch_btn").click().run()
        self.assertFalse(app.exception, [str(e.value) for e in app.exception])
        return app

    # --- the live scenario lives beside the sliders ------------------------

    def test_the_live_scenario_is_not_a_row_in_the_list(self):
        app = self.open_simulator()
        self.assertNotIn("Current settings", row_names(app))

    def test_the_scenario_band_shows_the_implied_changes(self):
        app = self.open_simulator()
        stats = strip_stats(app)
        self.assertTrue(stats, "scenario band not rendered")
        for label in ("Future users", "Purchasing", "Orders", "Gross value"):
            self.assertIn(label, stats)

    def test_the_band_lays_the_four_figures_out_side_by_side(self):
        """
        Stacked in a column this was six lines and about 265px, which set the
        height of the whole control row and left the sliders in a
        quarter-screen of nothing.
        """
        app = self.open_simulator()
        self.assertEqual(strip_stats(app).count("clue-strip-stat\">"), 4)

    def test_the_band_follows_the_sliders(self):
        app = self.open_simulator()
        headline = lambda: re.search(
            r'clue-strip-value">([^<]*)', strip_head(app)
        ).group(1)
        before = headline()
        app.slider(key="sim_conversion").set_value(41.0).run()
        self.assertNotEqual(before, headline())

    def test_the_band_does_not_repeat_the_assumptions(self):
        """The three sliders directly above it are the assumptions."""
        app = self.open_simulator()
        self.assertNotIn("Assumptions", strip_head(app) + strip_stats(app))

    def test_the_band_shares_a_card_with_the_inputs(self):
        """
        One block with two halves, divided by a rule -- the band is what the
        sliders above it produce, and two separate cards read as two unrelated
        things. The readout that used to be a fifth column is what made the
        input row twice as tall as it needed to be.
        """
        app = self.open_simulator()
        self.assertNotIn("clue-live-headline", markdown_text(app))
        self.assertIn("clue-strip-stats", markdown_text(app))

        css = next(
            block.value for block in app.markdown
            if ".st-key-scenario_strip {" in block.value
        )
        rule = css[css.index(".st-key-scenario_strip {"):]
        rule = rule[: rule.index("}")]
        self.assertIn("border-top:", rule)

        # A structural split, so it carries more weight than the hairline
        # between adjacent figures -- at that weight it was invisible.
        from components.styles import CARD_DIVIDER, CARD_RULE

        self.assertIn(CARD_DIVIDER, rule)
        self.assertNotIn(CARD_RULE, rule)

    # --- the results panel is driven by selection alone --------------------

    def test_nothing_selected_shows_a_hint_not_a_graph(self):
        """
        There is nothing to propagate until a scenario is chosen, and the
        sliders' own numbers are already on screen in the control row.
        """
        app = self.open_simulator()
        self.assertTrue(shows_hint(app))
        self.assertEqual(results_heading(app), "###### Simulation Results")

    def test_selecting_a_row_replaces_the_hint_with_its_results(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        app.button(key="select_A").click().run()
        self.assertFalse(shows_hint(app))
        self.assertIn("Scenario A", results_heading(app))

    def test_there_is_no_simulate_button(self):
        """Clicking a row is the whole interaction."""
        app = self.open_simulator()
        self.assertNotIn("start_simulation", {b.key for b in app.button})

    def test_deselecting_returns_to_the_hint(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        app.button(key="select_A").click().run()
        app.button(key="select_A").click().run()
        self.assertTrue(shows_hint(app))
        self.assertEqual(selected_count(app), 0)

    # --- selection ---------------------------------------------------------

    def test_the_selected_row_is_visibly_marked(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        self.assertNotIn("is-selected", list_html(app))

        app.button(key="select_A").click().run()
        html = list_html(app)
        self.assertEqual(html.count("clue-lite is-selected"), 1)
        selected = html[html.index("clue-lite is-selected"):]
        self.assertIn("Scenario A", selected[:200])

    def test_only_one_row_is_marked_at_a_time(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        app.slider(key="sim_conversion").set_value(40.0).run()
        app.button(key="pin_scenario").click().run()
        app.button(key="select_A").click().run()
        app.button(key="select_B").click().run()
        self.assertEqual(selected_count(app), 1)
        self.assertIn("Scenario B", results_heading(app))

    def test_removing_the_selected_row_returns_to_the_hint(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        app.button(key="select_A").click().run()
        app.button(key="remove_A").click().run()
        self.assertFalse(app.exception)
        self.assertNotIn("Scenario A", row_names(app))
        self.assertTrue(shows_hint(app))

    def test_the_reference_row_can_be_dismissed(self):
        app = self.open_simulator()
        self.assertIn("Best observed", row_names(app))
        app.button(key="remove___reference__").click().run()
        self.assertNotIn("Best observed", row_names(app))

    # --- pinning -----------------------------------------------------------

    def test_pinning_adds_a_row_and_leaves_the_sliders_alone(self):
        app = self.open_simulator()
        app.slider(key="sim_conversion").set_value(41.0).run()
        app.button(key="pin_scenario").click().run()
        self.assertIn("Scenario A", row_names(app))
        self.assertEqual(app.slider(key="sim_conversion").value, 41.0)

    def test_rows_are_lettered_in_order(self):
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        app.slider(key="sim_conversion").set_value(40.0).run()
        app.button(key="pin_scenario").click().run()
        self.assertEqual(
            [n for n in row_names(app) if n.startswith("Scenario")],
            ["Scenario A", "Scenario B"],
        )

    def test_the_list_fills_to_six_slots(self):
        """Six in total, one of them the "Best observed" starting point."""
        app = self.open_simulator()
        for step in range(5):
            app.slider(key="sim_conversion").set_value(35.0 + step).run()
            app.button(key="pin_scenario").click().run()

        names = row_names(app)
        self.assertEqual(len(names), 6, names)
        self.assertEqual(names[0], "Best observed")
        self.assertIn("List is full", app.button(key="pin_scenario").label)

    def test_dismissing_the_reference_row_frees_a_slot(self):
        app = self.open_simulator()
        for step in range(5):
            app.slider(key="sim_conversion").set_value(35.0 + step).run()
            app.button(key="pin_scenario").click().run()
        self.assertIn("List is full", app.button(key="pin_scenario").label)

        app.button(key="remove___reference__").click().run()
        self.assertNotIn("List is full", app.button(key="pin_scenario").label)
        app.button(key="pin_scenario").click().run()
        self.assertEqual(len(row_names(app)), 6)

    # --- each row carries what tells scenarios apart -----------------------

    def test_a_row_shows_its_headline_and_assumptions(self):
        app = self.open_simulator()
        app.slider(key="sim_conversion").set_value(41.0).run()
        app.button(key="pin_scenario").click().run()
        html = list_html(app)
        row = html[html.index("Scenario A"):]
        self.assertRegex(row, r'clue-lite-val">\$[\d,.]+<')
        self.assertRegex(row, r'clue-lite-sub">41\.0% · [\d.]+ · \$[\d.]+<')

    def test_rows_do_not_carry_the_implied_pathway(self):
        """It moved to the results panel, which is what lets six rows fit."""
        app = self.open_simulator()
        app.button(key="pin_scenario").click().run()
        self.assertNotIn("Implied pathway", list_html(app))


if __name__ == "__main__":
    unittest.main()
