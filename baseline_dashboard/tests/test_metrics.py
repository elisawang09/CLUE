"""Tests for the metric computations and the required consistency checks."""

import unittest

import numpy as np
import pandas as pd

from metrics.checks import run_checks
from metrics.compute import (
    WINDOW_CHOICES,
    CohortFilter,
    chart_frame,
    compute,
)
from metrics.registry import CARD_IDS, METRICS, formatted_value


def month(text: str) -> pd.Period:
    return pd.Period(text, freq="M")


class TestKnownCohort(unittest.TestCase):
    """
    A hand-built cohort whose answers can be worked out on paper.

    5 acquired users, 2 of whom purchase:
      U1: month 1 -> 2 orders / $60,  month 3 -> 1 order / $20
      U2: month 1 -> 1 order  / $20
      U3, U4, U5: never order
      U6: acquired outside the reference period, must be excluded entirely

    Conversion       = 2/5   = 0.4
    Orders/purchaser  = 4/2   = 2.0
    AOV               = 100/4 = 25.0
    Customer value    = 0.4 * 2.0 * 25.0 = 20.0  ( = $100 / 5 users )
    """

    def setUp(self):
        self.customers = pd.DataFrame(
            {
                "user_id": ["U1", "U2", "U3", "U4", "U5", "U6"],
                "acquisition_month": [
                    month("2022-01"), month("2022-02"), month("2022-01"),
                    month("2022-03"), month("2022-03"), month("2021-12"),
                ],
                "is_purchaser": [True, True, False, False, False, True],
            }
        )
        self.age_facts = pd.DataFrame(
            {
                "user_id": ["U1", "U1", "U2", "U6"],
                "customer_age_month": [1, 3, 1, 1],
                "orders": [2, 1, 1, 9],
                "gross_value": [60.0, 20.0, 20.0, 999.0],
            }
        )
        self.cohort = CohortFilter(month("2022-01"), month("2022-03"), window=6)
        self.metrics = compute(self.customers, self.age_facts, self.cohort)

    def test_counts(self):
        self.assertEqual(self.metrics.acquired_users, 5)
        self.assertEqual(self.metrics.purchasing_customers, 2)
        self.assertEqual(self.metrics.total_orders, 4)
        self.assertAlmostEqual(self.metrics.total_gross_order_value, 100.0)

    def test_ratios(self):
        self.assertAlmostEqual(self.metrics.conversion_rate, 0.4)
        self.assertAlmostEqual(self.metrics.orders_per_purchasing_customer, 2.0)
        self.assertAlmostEqual(self.metrics.average_order_value, 25.0)
        self.assertAlmostEqual(self.metrics.customer_value, 20.0)

    def test_users_outside_the_reference_period_are_excluded(self):
        self.assertNotIn("U6", self.metrics.user_ids)
        self.assertAlmostEqual(self.metrics.total_gross_order_value, 100.0)

    def test_monthly_contribution_spreads_over_all_acquired_users(self):
        # $80 in month 1 over 5 acquired users, $20 in month 3.
        contribution = self.metrics.monthly_contribution
        self.assertAlmostEqual(contribution[1], 16.0)
        self.assertAlmostEqual(contribution[2], 0.0)
        self.assertAlmostEqual(contribution[3], 4.0)
        self.assertEqual(list(contribution.index), [1, 2, 3, 4, 5, 6])

    def test_cumulative_is_the_running_sum(self):
        expected = self.metrics.monthly_contribution.cumsum()
        pd.testing.assert_series_equal(self.metrics.cumulative_value, expected)
        self.assertAlmostEqual(self.metrics.cumulative_value.iloc[-1], 20.0)

    def test_window_narrows_the_observation(self):
        narrow = compute(
            self.customers,
            self.age_facts,
            CohortFilter(month("2022-01"), month("2022-03"), window=2),
        )
        # U1's month-3 order now falls outside the window.
        self.assertEqual(narrow.total_orders, 3)
        self.assertAlmostEqual(narrow.total_gross_order_value, 80.0)
        self.assertAlmostEqual(narrow.customer_value, 16.0)

    def test_all_consistency_checks_pass(self):
        for result in run_checks(self.metrics):
            self.assertTrue(result.passed, f"{result.name}: {result.detail}")

    def test_chart_frame_matches_the_series(self):
        frame = chart_frame(self.metrics)
        self.assertEqual(len(frame), 6)
        self.assertAlmostEqual(frame.cumulative_value.iloc[-1],
                               self.metrics.customer_value)
        self.assertAlmostEqual(frame.monthly_contribution.sum(),
                               self.metrics.customer_value)


class TestEmptyCohort(unittest.TestCase):
    """A period with no acquisitions must degrade quietly, not divide by zero."""

    def setUp(self):
        customers = pd.DataFrame(
            {"user_id": ["U1"], "acquisition_month": [month("2022-01")],
             "is_purchaser": [True]}
        )
        age_facts = pd.DataFrame(
            {"user_id": ["U1"], "customer_age_month": [1], "orders": [1],
             "gross_value": [10.0]}
        )
        self.metrics = compute(
            customers, age_facts,
            CohortFilter(month("2023-01"), month("2023-03"), window=6),
        )

    def test_counts_are_zero(self):
        self.assertEqual(self.metrics.acquired_users, 0)
        self.assertEqual(self.metrics.total_orders, 0)

    def test_ratios_are_nan_not_errors(self):
        self.assertTrue(np.isnan(self.metrics.conversion_rate))
        self.assertTrue(np.isnan(self.metrics.customer_value))

    def test_formatted_values_show_a_dash(self):
        self.assertEqual(formatted_value("customer_value", self.metrics), "—")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        customers = pd.DataFrame(
            {"user_id": ["U1", "U2"],
             "acquisition_month": [month("2022-01")] * 2,
             "is_purchaser": [True, False]}
        )
        age_facts = pd.DataFrame(
            {"user_id": ["U1"], "customer_age_month": [1], "orders": [4],
             "gross_value": [100.0]}
        )
        self.metrics = compute(
            customers, age_facts,
            CohortFilter(month("2022-01"), month("2022-01"), window=6),
        )

    def test_five_kpi_cards(self):
        self.assertEqual(len(CARD_IDS), 5)
        self.assertEqual(CARD_IDS[0], "customer_value")

    def test_names_follow_the_observation_window(self):
        self.assertEqual(
            METRICS["customer_value"].name(self.metrics), "6-Month Customer Value"
        )
        nine = compute(
            pd.DataFrame({"user_id": ["U1"],
                          "acquisition_month": [month("2022-01")],
                          "is_purchaser": [True]}),
            pd.DataFrame({"user_id": ["U1"], "customer_age_month": [1],
                          "orders": [1], "gross_value": [1.0]}),
            CohortFilter(month("2022-01"), month("2022-01"), window=9),
        )
        self.assertEqual(
            METRICS["customer_value"].name(nine), "9-Month Customer Value"
        )

    def test_every_expression_reference_resolves(self):
        for metric in METRICS.values():
            for token in metric.expression(self.metrics):
                if token.ref is not None:
                    self.assertIn(
                        token.ref, METRICS,
                        f"{metric.id} links to unknown metric {token.ref}",
                    )

    def test_every_metric_formats_without_error(self):
        for metric_id in METRICS:
            self.assertIsInstance(formatted_value(metric_id, self.metrics), str)

    def test_period_label(self):
        self.assertEqual(
            CohortFilter(month("2022-01"), month("2022-03")).label, "Jan-Mar 2022"
        )
        self.assertEqual(
            CohortFilter(month("2022-02"), month("2022-02")).label, "Feb 2022"
        )
        self.assertEqual(
            CohortFilter(month("2021-12"), month("2022-02")).label,
            "Dec 2021-Feb 2022",
        )


class TestAgainstRealData(unittest.TestCase):
    """
    The four required checks, across every cohort and window on the real
    modeled data -- not just the dashboard's default.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from datasource.loader import load_age_facts, load_customers

            cls.customers = load_customers()
            cls.age_facts = load_age_facts()
        except Exception as exc:  # data not built yet
            raise unittest.SkipTest(f"modeled data unavailable: {exc}")

    def test_checks_pass_for_every_cohort_and_window(self):
        months = pd.PeriodIndex(sorted(self.customers.acquisition_month.unique()),
                                freq="M")
        checked = 0
        for window in WINDOW_CHOICES:
            for i in range(0, len(months) - 2, 4):  # sampled 3-month windows
                cohort = CohortFilter(months[i], months[i + 2], window=window)
                metrics = compute(self.customers, self.age_facts, cohort)
                for result in run_checks(metrics):
                    self.assertTrue(
                        result.passed,
                        f"{cohort.label} w{window} -- {result.name}: {result.detail}",
                    )
                checked += 1
        self.assertGreater(checked, 20)

    def test_full_range_reconciles(self):
        months = pd.PeriodIndex(sorted(self.customers.acquisition_month.unique()),
                                freq="M")
        metrics = compute(
            self.customers, self.age_facts,
            CohortFilter(months[0], months[-1], window=12),
        )
        self.assertEqual(metrics.acquired_users, len(self.customers))
        self.assertEqual(
            metrics.purchasing_customers, int(self.customers.is_purchaser.sum())
        )
        self.assertAlmostEqual(
            metrics.customer_value,
            metrics.total_gross_order_value / metrics.acquired_users,
            places=6,
        )

    def test_non_purchasers_reconcile(self):
        months = pd.PeriodIndex(sorted(self.customers.acquisition_month.unique()),
                                freq="M")
        metrics = compute(
            self.customers, self.age_facts,
            CohortFilter(months[0], months[-1], window=12),
        )
        non_purchasers = metrics.acquired_users - metrics.purchasing_customers
        self.assertEqual(
            non_purchasers, int((~self.customers.is_purchaser).sum())
        )
        self.assertGreater(non_purchasers, 0)


if __name__ == "__main__":
    unittest.main()
