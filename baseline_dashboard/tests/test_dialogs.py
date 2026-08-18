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


class TestMetricDetails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import streamlit.testing.v1  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")

    def test_opening_details_shows_the_calculation(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        self.assertFalse(app.exception)

        text = all_text(app)
        self.assertIn("6-Month Customer Value", text)
        self.assertIn("Description", text)
        self.assertIn("Calculation", text)
        self.assertIn("Reference acquisition period", text)
        self.assertIn("Jan-Mar 2022", text)
        self.assertIn("Observation window", text)

    def test_components_are_shown_with_their_values(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        text = all_text(app)

        # The three factors and the values that multiply out to the headline.
        self.assertIn("6-Month Purchase Conversion Rate", text)
        self.assertIn("Orders per Purchasing Customer", text)
        self.assertIn("Average Order Value", text)
        self.assertIn("36.1%", text)
        self.assertIn("55.2", text)
        self.assertIn("$8.08", text)

    def test_drilling_into_a_component(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        app.button(key="drill_average_order_value").click().run()
        self.assertFalse(app.exception)

        text = all_text(app)
        self.assertIn("Total Gross Order Value", text)
        self.assertIn("Total Orders", text)
        # Breadcrumb shows the path taken.
        self.assertIn("6-Month Customer Value › Average Order Value", text)

    def test_drilling_all_the_way_to_gross_value(self):
        """The chain the spec requires: headline down to revenue - cost."""
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        app.button(key="drill_average_order_value").click().run()
        app.button(key="drill_total_gross_order_value").click().run()
        app.button(key="drill_gross_value").click().run()
        self.assertFalse(app.exception)

        text = all_text(app)
        self.assertIn("revenue − cost", text)
        self.assertIn("gross_value", text)

    def test_back_returns_to_the_previous_metric(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        app.button(key="drill_average_order_value").click().run()
        app.button(key="details_back").click().run()
        self.assertFalse(app.exception)

        text = all_text(app)
        self.assertIn("6-Month Customer Value", text)
        self.assertNotIn("› Average Order Value", text)

    def test_close_dismisses_the_panel(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        app.button(key="details_close").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["open_panel"])
        self.assertEqual(app.session_state["metric_nav"], [])

    def test_every_card_opens_its_own_details(self):
        for metric_id in (
            "conversion_rate", "orders_per_purchasing_customer",
            "average_order_value", "acquired_users",
        ):
            with self.subTest(metric=metric_id):
                app = fresh_app()
                app.button(key=f"details_{metric_id}").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["metric_nav"], [metric_id])


class TestUnderlyingData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import streamlit.testing.v1  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")

    def open_underlying(self):
        app = fresh_app()
        app.button(key="details_customer_value").click().run()
        app.button(key="details_underlying").click().run()
        return app

    def test_opens_from_metric_details(self):
        app = self.open_underlying()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["open_panel"], "underlying")

    def test_summary_tab_shows_the_cohort(self):
        app = self.open_underlying()
        frames = [df.value for df in app.dataframe]
        self.assertTrue(frames, "no dataframe rendered")

        summary = frames[0]
        self.assertIn("Acquired Users", summary.columns)
        self.assertEqual(summary["Acquired Users"].iloc[0], 1234)
        self.assertEqual(summary["Purchasing Customers"].iloc[0], 446)

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
        for column in ("revenue", "cost", "gross_value", "customer_age_month"):
            self.assertIn(column, order_frames[0].columns)

    def _exports(self, app) -> dict[str, str]:
        """
        Export buttons keyed by our own key, mapped to their label.

        AppTest exposes no download_button accessor, and the proto serves the
        file by URL rather than inline, so the label is what is checkable here.
        The exported bytes are asserted directly against the row builders in
        test_underlying_data.py.
        """
        return {
            element.proto.id.rsplit("-", 1)[-1]: element.proto.label
            for element in app.get("download_button")
        }

    def test_summary_export_is_offered(self):
        app = self.open_underlying()
        self.assertIn("dl_summary", self._exports(app))

    def test_row_export_covers_every_row_not_just_the_page(self):
        app = self.open_underlying()
        exports = self._exports(app)
        self.assertIn("dl_rows", exports)
        # 1,234 acquired users, while the table itself only displays 200.
        self.assertIn("1,234 rows", exports["dl_rows"])
        self.assertEqual(app.number_input(key="underlying_row_count").value, 200)

    def test_back_returns_to_details(self):
        app = self.open_underlying()
        app.button(key="underlying_back").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["open_panel"], "details")

    def test_close_dismisses(self):
        app = self.open_underlying()
        app.button(key="underlying_close").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["open_panel"])


if __name__ == "__main__":
    unittest.main()
