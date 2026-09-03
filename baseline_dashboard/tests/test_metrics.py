"""Tests for the metric computations and the required consistency checks."""

import unittest

import numpy as np
import pandas as pd

from metrics.checks import run_checks
from metrics.compute import (
    WINDOW_DAYS,
    CohortFilter,
    chart_frame,
    compute,
    month_table,
)
from metrics.registry import CARD_IDS, METRICS, formatted_value


def month(text: str) -> pd.Period:
    return pd.Period(text, freq="M")


def customers(rows: list[tuple[str, str]]) -> pd.DataFrame:
    """(user_id, acquisition month) pairs as the customers frame."""
    return pd.DataFrame(
        {
            "user_id": [user for user, _ in rows],
            "acquisition_month": [month(m) for _, m in rows],
        }
    )


def window_facts(rows: list[tuple[str, int, float]]) -> pd.DataFrame:
    """(user_id, orders, gross_value) triples, already windowed to 90 days."""
    return pd.DataFrame(
        {
            "user_id": [user for user, _, _ in rows],
            "orders": [orders for _, orders, _ in rows],
            "gross_value": [value for _, _, value in rows],
        }
    )


class TestKnownCohort(unittest.TestCase):
    """
    A hand-built set of cohorts whose answers can be worked out on paper.

    Mar 2022 is the latest month in the reference period, so it is the one the
    cards report:
      U4: 4 orders / $100    U5, U6: never order
      Conversion      = 1/3   = 0.3333...
      Orders/customer = 4/1   = 4.0
      AOV             = 100/4 = 25.0
      Customer value  = 100/3 = 33.333...

    Feb 2022 is the comparison month:
      U2, U3 acquired, U2 places 2 orders / $40
      Customer value  = 40/2  = 20.0
    """

    def setUp(self):
        self.customers = customers(
            [
                ("U1", "2022-01"),
                ("U2", "2022-02"), ("U3", "2022-02"),
                ("U4", "2022-03"), ("U5", "2022-03"), ("U6", "2022-03"),
            ]
        )
        self.window_facts = window_facts(
            [("U1", 1, 10.0), ("U2", 2, 40.0), ("U4", 4, 100.0)]
        )
        self.cohort = CohortFilter(month("2022-01"), month("2022-03"))
        self.metrics = compute(self.customers, self.window_facts, self.cohort)

    def test_cards_report_the_latest_month(self):
        self.assertEqual(self.metrics.latest.month, month("2022-03"))
        self.assertEqual(self.metrics.acquired_users, 3)
        self.assertEqual(self.metrics.purchasing_customers, 1)
        self.assertEqual(self.metrics.total_orders, 4)
        self.assertAlmostEqual(self.metrics.total_gross_order_value, 100.0)

    def test_factors(self):
        self.assertAlmostEqual(self.metrics.conversion_rate, 1 / 3)
        self.assertAlmostEqual(self.metrics.orders_per_purchasing_customer, 4.0)
        self.assertAlmostEqual(self.metrics.average_order_value, 25.0)
        self.assertAlmostEqual(self.metrics.customer_value, 100 / 3)

    def test_headline_is_the_product_of_its_factors(self):
        self.assertAlmostEqual(
            self.metrics.customer_value,
            self.metrics.conversion_rate
            * self.metrics.orders_per_purchasing_customer
            * self.metrics.average_order_value,
        )

    def test_previous_month_is_the_one_before(self):
        self.assertIsNotNone(self.metrics.previous)
        self.assertEqual(self.metrics.previous.month, month("2022-02"))
        self.assertAlmostEqual(self.metrics.previous.customer_value, 20.0)

    def test_delta_against_the_previous_month(self):
        self.assertAlmostEqual(
            self.metrics.delta("customer_value"), 100 / 3 - 20.0
        )
        self.assertAlmostEqual(
            self.metrics.delta_ratio("customer_value"), (100 / 3 - 20.0) / 20.0
        )
        self.assertEqual(self.metrics.delta("acquired_users"), 1)

    def test_by_month_covers_every_month_in_the_period(self):
        self.assertEqual(
            list(self.metrics.by_month.acquisition_month),
            [month("2022-01"), month("2022-02"), month("2022-03")],
        )

    def test_chart_frame_marks_the_month_the_cards_report(self):
        frame = chart_frame(self.metrics)
        latest = frame[frame.is_latest]
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest.iloc[0].month_label, "Mar 2022")
        self.assertAlmostEqual(latest.iloc[0].customer_value, 100 / 3)

    def test_all_checks_pass(self):
        for result in run_checks(self.metrics):
            self.assertTrue(result.passed, f"{result.name}: {result.detail}")


class TestPreviousMonthReachesOutsideTheSelection(unittest.TestCase):
    """
    The comparison is against the previous month in the *data*, not in the
    selection -- otherwise a single-month period would never show a delta.
    """

    def setUp(self):
        self.customers = customers(
            [("U1", "2022-01"), ("U2", "2022-02"), ("U3", "2022-03")]
        )
        self.window_facts = window_facts(
            [("U1", 1, 10.0), ("U2", 1, 20.0), ("U3", 1, 30.0)]
        )

    def test_single_month_period_still_has_a_previous(self):
        metrics = compute(
            self.customers,
            self.window_facts,
            CohortFilter(month("2022-03"), month("2022-03")),
        )
        self.assertEqual(len(metrics.by_month), 1)
        self.assertIsNotNone(metrics.previous)
        self.assertEqual(metrics.previous.month, month("2022-02"))
        self.assertAlmostEqual(metrics.delta("customer_value"), 10.0)

    def test_earliest_month_in_the_data_has_no_previous(self):
        metrics = compute(
            self.customers,
            self.window_facts,
            CohortFilter(month("2022-01"), month("2022-01")),
        )
        self.assertIsNone(metrics.previous)
        self.assertIsNone(metrics.delta("customer_value"))
        self.assertIsNone(metrics.delta_ratio("customer_value"))


class TestEmptyCohort(unittest.TestCase):
    """A period with no acquisitions must degrade quietly, not divide by zero."""

    def setUp(self):
        self.metrics = compute(
            customers([("U1", "2022-01")]),
            window_facts([("U1", 1, 10.0)]),
            CohortFilter(month("2023-01"), month("2023-03")),
        )

    def test_counts_are_zero(self):
        self.assertEqual(self.metrics.acquired_users, 0)
        self.assertEqual(self.metrics.total_orders, 0)

    def test_ratios_are_nan_not_errors(self):
        self.assertTrue(np.isnan(self.metrics.conversion_rate))
        self.assertTrue(np.isnan(self.metrics.customer_value))

    def test_no_previous_month_and_no_delta(self):
        self.assertIsNone(self.metrics.previous)
        self.assertIsNone(self.metrics.delta("customer_value"))

    def test_by_month_is_empty(self):
        self.assertTrue(self.metrics.by_month.empty)

    def test_formatted_values_show_a_dash(self):
        self.assertEqual(formatted_value("customer_value", self.metrics), "—")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.metrics = compute(
            customers([("U1", "2022-01"), ("U2", "2022-01")]),
            window_facts([("U1", 4, 100.0)]),
            CohortFilter(month("2022-01"), month("2022-01")),
        )

    def test_five_kpi_cards(self):
        self.assertEqual(len(CARD_IDS), 5)
        self.assertEqual(CARD_IDS[0], "customer_value")

    def test_names_carry_the_fixed_window(self):
        self.assertEqual(
            METRICS["customer_value"].name(self.metrics), "90-Day Customer Value"
        )
        self.assertEqual(
            METRICS["conversion_rate"].name(self.metrics),
            "90-Day Purchase Conversion Rate",
        )

    def test_descriptions_name_the_cohort_month_the_cards_report(self):
        description = METRICS["acquired_users"].description(self.metrics)
        self.assertIn("Jan 2022", description)

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
    """The required checks, across every cohort on the real modeled data."""

    @classmethod
    def setUpClass(cls):
        try:
            from datasource.loader import load_customers, load_window_facts

            cls.customers = load_customers()
            cls.window_facts = load_window_facts()
        except Exception as exc:  # data not built yet
            raise unittest.SkipTest(f"modeled data unavailable: {exc}")

        cls.months = pd.PeriodIndex(
            sorted(cls.customers.acquisition_month.unique()), freq="M"
        )

    def test_checks_pass_for_every_cohort(self):
        checked = 0
        for i in range(0, len(self.months) - 2, 2):  # sampled 3-month periods
            cohort = CohortFilter(self.months[i], self.months[i + 2])
            metrics = compute(self.customers, self.window_facts, cohort)
            for result in run_checks(metrics):
                self.assertTrue(
                    result.passed,
                    f"{cohort.label} -- {result.name}: {result.detail}",
                )
            checked += 1
        self.assertGreater(checked, 20)

    def test_every_month_reconciles_to_its_own_users(self):
        """Per-month acquired users must total the whole customer table."""
        table = month_table(self.customers, self.window_facts)
        self.assertEqual(int(table.acquired_users.sum()), len(self.customers))

    def test_cards_match_the_last_bar_on_the_chart(self):
        cohort = CohortFilter(self.months[0], self.months[-1])
        metrics = compute(self.customers, self.window_facts, cohort)
        frame = chart_frame(metrics)

        latest = frame[frame.is_latest]
        self.assertEqual(len(latest), 1)
        self.assertAlmostEqual(
            float(latest.iloc[0].customer_value), metrics.customer_value, places=9
        )
        self.assertEqual(
            int(latest.iloc[0].acquired_users), metrics.acquired_users
        )

    def test_full_range_covers_every_month(self):
        cohort = CohortFilter(self.months[0], self.months[-1])
        metrics = compute(self.customers, self.window_facts, cohort)
        self.assertEqual(len(metrics.by_month), len(self.months))
        self.assertEqual(metrics.latest.month, self.months[-1])

    def test_non_purchasers_exist_in_every_sampled_cohort(self):
        """
        The headline is value per *acquired* user, so a cohort where everyone
        purchased would quietly collapse it to orders x AOV.
        """
        table = month_table(self.customers, self.window_facts)
        non_purchasers = table.acquired_users - table.purchasing_customers
        self.assertTrue(
            (non_purchasers > 0).all(),
            "a cohort month has no non-purchasing acquired users",
        )

    def test_window_is_fixed_at_ninety_days(self):
        self.assertEqual(WINDOW_DAYS, 90)


if __name__ == "__main__":
    unittest.main()
