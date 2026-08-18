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

APP = str(Path(__file__).resolve().parent.parent / "app.py")


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
            "6-Month Customer Value",
            "6-Month Purchase Conversion Rate",
            "Orders per Purchasing Customer",
            "Average Order Value",
            "Acquired Users",
        ):
            self.assertIn(expected, labels, f"missing KPI card: {expected}")

    def test_default_cohort_headline(self):
        markdown = " ".join(m.value for m in self.app.markdown)
        self.assertIn("$161.25", markdown, "headline value not rendered")
        self.assertIn("1,234", markdown, "acquired users not rendered")

    def test_both_chart_titles_present(self):
        markdown = " ".join(m.value for m in self.app.markdown)
        self.assertIn("Customer Value in the First 6 Months", markdown)
        self.assertIn("Monthly Value Contribution", markdown)

    def test_filters_present(self):
        self.assertEqual(len(self.app.selectbox), 3)
        keys = {box.key for box in self.app.selectbox}
        self.assertEqual(keys, {"filter_start", "filter_end", "filter_window"})

    def test_metric_details_buttons_present(self):
        keys = {button.key for button in self.app.button}
        for metric_id in (
            "customer_value", "conversion_rate", "orders_per_purchasing_customer",
            "average_order_value", "acquired_users",
        ):
            self.assertIn(f"details_{metric_id}", keys)

    def test_changing_the_window_changes_the_headline(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(APP, default_timeout=120).run()
        app.selectbox(key="filter_window").select(12).run()
        self.assertFalse(app.exception)
        markdown = " ".join(m.value for m in app.markdown)
        self.assertIn("12-Month Customer Value", markdown)
        self.assertNotIn("$161.25", markdown)


if __name__ == "__main__":
    unittest.main()
