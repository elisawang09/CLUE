"""
End-to-end interaction tests for the two dialogs.

These walk the sequence the study task asks a participant to perform: open the
metric, read the calculation, step into a component, come back, open the
underlying data, export it.
"""

# Redirect interaction logging away from the real study log before the app
# is imported or driven; see study.events.use_temporary_log_dir.
from study.events import use_temporary_log_dir

use_temporary_log_dir()

import unittest
from pathlib import Path

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def fresh_app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(APP, default_timeout=180).run()


def all_text(app) -> str:
    parts = [m.value for m in app.markdown]
    parts += [c.value for c in app.caption]
    parts += [str(h.value) for h in app.subheader]
    return " ".join(parts)


class TestUnderlyingData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import streamlit.testing.v1  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")

    def open_underlying(self):
        """The card menu is now the only way in -- Metric Details is gone."""
        app = fresh_app()
        app.button(key="underlying_customer_value").click().run()
        return app

    def test_opens_straight_from_the_card_menu(self):
        app = self.open_underlying()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["open_panel"], "underlying")

    def test_summary_tab_shows_the_cohort(self):
        app = self.open_underlying()
        frames = [df.value for df in app.dataframe]
        self.assertTrue(frames, "no dataframe rendered")

        summary = frames[0]
        self.assertIn("Acquired Users", summary.columns)
        # The cards, and so the summary, report Jun 2024 -- the latest month
        # in the default Jan-Jun 2024 period, not the period as a whole.
        self.assertEqual(summary["Acquisition Month"].iloc[0], "Jun 2024")
        self.assertEqual(summary["Acquired Users"].iloc[0], 31)

    def test_both_grains_are_offered(self):
        app = self.open_underlying()
        options = list(app.radio(key="underlying_grain").options)
        self.assertEqual(
            options, ["One row per acquired user", "One row per order"]
        )

    def test_switching_to_order_grain(self):
        app = self.open_underlying()
        app.radio(key="underlying_grain").set_value("One row per order").run()
        self.assertFalse(app.exception)

        frames = [df.value for df in app.dataframe]
        order_frames = [f for f in frames if "order_id" in f.columns]
        self.assertTrue(order_frames, "order-grain table not rendered")
        for column in ("revenue", "cost", "gross_value", "days_since_acquisition"):
            self.assertIn(column, order_frames[0].columns)

    def test_no_csv_export_is_offered(self):
        """The tables are for reading on screen; nothing is downloadable."""
        app = self.open_underlying()
        self.assertEqual(list(app.get("download_button")), [])

    def test_row_count_defaults_to_at_most_a_page(self):
        """
        The default cohort is small enough that the page size collapses to the
        widget's floor, so this pins the range rather than an exact value.
        """
        app = self.open_underlying()
        value = app.number_input(key="underlying_row_count").value
        self.assertGreaterEqual(value, 10)
        self.assertLessEqual(value, 200)

    def test_close_dismisses(self):
        app = self.open_underlying()
        app.button(key="underlying_close").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["open_panel"])


if __name__ == "__main__":
    unittest.main()
