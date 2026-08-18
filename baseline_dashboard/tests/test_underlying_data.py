"""
Tests for the underlying-data row builders.

These are the tables a participant is expected to check the headline against by
hand, so they have to reconcile exactly with the KPIs -- that is the whole point
of the view.
"""

# Redirect interaction logging away from the real study log before the app
# is imported or driven; see study.events.use_temporary_log_dir.
from study.events import use_temporary_log_dir

use_temporary_log_dir()

import unittest

import pandas as pd

from metrics.compute import CohortFilter, compute


class TestRowBuildersAgainstRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from components.underlying_data import (
                customer_rows,
                order_rows,
                period_summary,
            )
            from datasource.loader import load_age_facts, load_customers
        except Exception as exc:
            raise unittest.SkipTest(f"modeled data unavailable: {exc}")

        cls.customer_rows = staticmethod(customer_rows)
        cls.order_rows = staticmethod(order_rows)
        cls.period_summary = staticmethod(period_summary)

        cls.customers = load_customers()
        cls.age_facts = load_age_facts()
        cls.cohort = CohortFilter(
            pd.Period("2022-01"), pd.Period("2022-03"), window=6
        )
        cls.metrics = compute(cls.customers, cls.age_facts, cls.cohort)

    # --- customer grain ----------------------------------------------------

    def test_one_row_per_acquired_user(self):
        rows = self.customer_rows(self.metrics)
        self.assertEqual(len(rows), self.metrics.acquired_users)
        self.assertEqual(rows.user_id.nunique(), len(rows))

    def test_columns_follow_the_observation_window(self):
        rows = self.customer_rows(self.metrics)
        self.assertEqual(
            list(rows.columns),
            ["user_id", "acquisition_date", "purchasing_customer_6m",
             "orders_6m", "gross_value_6m"],
        )

    def test_purchaser_flag_reconciles_with_the_kpi(self):
        rows = self.customer_rows(self.metrics)
        self.assertEqual(
            int(rows.purchasing_customer_6m.sum()),
            self.metrics.purchasing_customers,
        )

    def test_non_purchasers_are_present_with_zeros(self):
        rows = self.customer_rows(self.metrics)
        non_purchasers = rows[rows.purchasing_customer_6m == 0]
        expected = self.metrics.acquired_users - self.metrics.purchasing_customers
        self.assertEqual(len(non_purchasers), expected)
        self.assertGreater(len(non_purchasers), 0)
        self.assertTrue((non_purchasers.orders_6m == 0).all())
        self.assertTrue((non_purchasers.gross_value_6m == 0).all())

    def test_totals_reconcile_with_the_kpis(self):
        rows = self.customer_rows(self.metrics)
        self.assertEqual(int(rows.orders_6m.sum()), self.metrics.total_orders)
        self.assertAlmostEqual(
            float(rows.gross_value_6m.sum()),
            self.metrics.total_gross_order_value,
            places=1,
        )

    def test_headline_is_recoverable_from_the_rows(self):
        """A participant dividing the two columns must land on the headline."""
        rows = self.customer_rows(self.metrics)
        by_hand = rows.gross_value_6m.sum() / len(rows)
        self.assertAlmostEqual(by_hand, self.metrics.customer_value, places=2)

    # --- order grain -------------------------------------------------------

    def test_order_rows_reconcile_with_total_orders(self):
        rows = self.order_rows(self.metrics, age_month=None)
        self.assertEqual(len(rows), self.metrics.total_orders)
        self.assertEqual(rows.order_id.nunique(), len(rows))

    def test_order_rows_gross_value_is_revenue_minus_cost(self):
        rows = self.order_rows(self.metrics, age_month=None)
        residual = (rows.revenue - rows.cost - rows.gross_value).abs().max()
        self.assertLess(residual, 0.011)

    def test_order_rows_sum_to_total_gross_order_value(self):
        rows = self.order_rows(self.metrics, age_month=None)
        self.assertAlmostEqual(
            float(rows.gross_value.sum()),
            self.metrics.total_gross_order_value,
            places=1,
        )

    def test_order_rows_stay_inside_the_window(self):
        rows = self.order_rows(self.metrics, age_month=None)
        self.assertTrue(rows.customer_age_month.between(1, 6).all())

    def test_selecting_a_month_narrows_the_rows(self):
        rows = self.order_rows(self.metrics, age_month=3)
        self.assertTrue((rows.customer_age_month == 3).all())
        self.assertLess(len(rows), self.metrics.total_orders)
        # And that month's gross value must match the chart's bar.
        expected = self.metrics.monthly_contribution[3] * self.metrics.acquired_users
        self.assertAlmostEqual(float(rows.gross_value.sum()), expected, places=1)

    def test_only_cohort_users_appear(self):
        rows = self.order_rows(self.metrics, age_month=None)
        self.assertTrue(set(rows.user_id).issubset(set(self.metrics.user_ids)))

    # --- summary -----------------------------------------------------------

    def test_period_summary_matches_the_cards(self):
        summary = self.period_summary(self.metrics).iloc[0]
        self.assertEqual(summary["Acquired Users"], self.metrics.acquired_users)
        self.assertEqual(
            summary["Purchasing Customers"], self.metrics.purchasing_customers
        )
        self.assertEqual(summary["Total Orders"], self.metrics.total_orders)
        self.assertAlmostEqual(
            summary["6-Month Customer Value"], self.metrics.customer_value
        )

    def test_csv_export_round_trips(self):
        import io

        rows = self.customer_rows(self.metrics)
        restored = pd.read_csv(io.StringIO(rows.to_csv(index=False)))
        self.assertEqual(len(restored), len(rows))
        self.assertEqual(list(restored.columns), list(rows.columns))
        self.assertAlmostEqual(
            restored.gross_value_6m.sum(), rows.gross_value_6m.sum(), places=1
        )


if __name__ == "__main__":
    unittest.main()
