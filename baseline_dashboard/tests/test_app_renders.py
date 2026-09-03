"""
Smoke test: the dashboard script runs end to end without raising, and puts the
expected numbers on screen.

Uses Streamlit's AppTest, which executes app.py in a real script runner, so an
exception in any component fails here rather than in front of a participant.
"""

# Redirect interaction logging away from the real study log before the app
# is imported or driven; see study.events.use_temporary_log_dir.
from study.events import use_temporary_log_dir

use_temporary_log_dir()

import unittest
from pathlib import Path

import pandas as pd

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def month_index(label: str) -> int:
    """
    Position of an acquisition month in the filter's options.

    The selectboxes hold integer indices and render them through a format_func,
    so a test has to select the index rather than the label it displays.
    """
    from datasource.loader import available_months

    return int(available_months().get_loc(pd.Period(label, freq="M")))


class TestDashboardRenders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")

        cls.app = AppTest.from_file(APP, default_timeout=120).run()

    def test_script_runs_without_exception(self):
        self.assertFalse(
            self.app.exception,
            "\n".join(str(e.value) for e in self.app.exception),
        )

    def test_no_consistency_error_banner(self):
        errors = [e.value for e in self.app.error]
        self.assertEqual(errors, [], f"error banner shown: {errors}")

    def test_five_kpi_cards_are_present(self):
        labels = " ".join(m.value for m in self.app.markdown)
        for expected in (
            "90-Day Customer Value",
            "90-Day Purchase Conversion Rate",
            "Orders per Purchasing Customer",
            "Average Order Value",
            "Acquired Users",
        ):
            self.assertIn(expected, labels, f"missing KPI card: {expected}")

    def test_cards_report_the_latest_month_in_the_period(self):
        """The default period is Jan-Jun 2024, so the cards describe Jun 2024."""
        markdown = " ".join(m.value for m in self.app.markdown)
        self.assertIn("$94.38", markdown, "headline value not rendered")
        self.assertIn("35.5%", markdown, "conversion rate not rendered")

    def test_every_card_names_the_month_it_describes(self):
        months = [
            m.value for m in self.app.markdown
            if 'class="bd-kpi-month"' in m.value
        ]
        self.assertEqual(len(months), 5, "expected one month line per card")
        for value in months:
            self.assertIn("Jun 2024", value)

    def test_cards_carry_a_delta_against_the_previous_month(self):
        markdown = " ".join(m.value for m in self.app.markdown)
        self.assertIn("vs May 2024", markdown, "no comparison month shown")
        # Jun 2024 is above May 2024 on the headline, while AOV fell -- both
        # directions are on screen.
        self.assertIn("bd-kpi-delta is-down", markdown)
        self.assertIn("bd-kpi-delta is-up", markdown)
        self.assertIn("▼", markdown)
        self.assertIn("▲", markdown)

    def test_both_chart_titles_present(self):
        markdown = " ".join(m.value for m in self.app.markdown)
        self.assertIn("90-Day Customer Value by Acquisition Month", markdown)
        self.assertIn(
            "90-Day Purchase Conversion Rate by Acquisition Month", markdown
        )

    def test_filters_present(self):
        """Only the acquisition period remains; the window is no longer a control."""
        self.assertEqual(len(self.app.selectbox), 2)
        keys = {box.key for box in self.app.selectbox}
        self.assertEqual(keys, {"filter_start", "filter_end"})

    def test_underlying_data_buttons_present(self):
        keys = {button.key for button in self.app.button}
        for metric_id in (
            "customer_value", "conversion_rate", "orders_per_purchasing_customer",
            "average_order_value", "acquired_users",
        ):
            self.assertIn(f"underlying_{metric_id}", keys)
            self.assertNotIn(f"details_{metric_id}", keys)

    def test_changing_the_period_moves_the_cards_to_a_new_month(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(APP, default_timeout=120).run()
        app.selectbox(key="filter_end").select(month_index("2024-05")).run()
        self.assertFalse(app.exception)

        markdown = " ".join(m.value for m in app.markdown)
        # The cards follow the end of the period, not its start.
        self.assertIn("vs Apr 2024", markdown)
        self.assertNotIn("vs May 2024", markdown)
        self.assertIn("$76.49", markdown)

    def test_a_single_month_period_still_shows_a_delta(self):
        """
        The comparison reaches one month back through the data, not through the
        selection -- otherwise narrowing to one month would drop the delta.
        """
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(APP, default_timeout=120).run()
        app.selectbox(key="filter_start").select(month_index("2024-03")).run()
        app.selectbox(key="filter_end").select(month_index("2024-03")).run()
        self.assertFalse(app.exception)

        markdown = " ".join(m.value for m in app.markdown)
        self.assertIn("vs Feb 2024", markdown)


if __name__ == "__main__":
    unittest.main()
