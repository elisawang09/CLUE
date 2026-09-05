"""
Tests for the provenance graph, the transformation flows, and scenario
propagation.

These exist mostly to stop the two apps silently desyncing again: the flows
describe a pipeline in prose and SQL, and prose does not fail loudly when the
window underneath it changes.
"""

import unittest

import pandas as pd

from data.graph_data import (
    EDGES,
    FLOW_IDS,
    LEAF_IDS,
    NODES,
    simulation_deltas,
    transformation_flow,
)
from data.metrics import WINDOW_DAYS, compute_baseline, node_values
from data.scenario import (
    Scenario,
    from_baseline,
    from_observed_best,
    goal_value,
    run_scenario_checks,
)


def all_text(nodes, edges) -> str:
    parts = []
    for node in nodes:
        parts += [node.label or "", node.description or ""]
    for edge in edges:
        parts += [edge.label or "", edge.description or ""]
    return " ".join(parts)


class TestProvenanceGraph(unittest.TestCase):
    def test_the_metric_is_named_by_its_window(self):
        labels = {node.id: node.label for node in NODES}
        self.assertEqual(labels["cust_val"], "90-Day Customer Value")
        self.assertEqual(labels["conv_rate"], "90-Day Purchase Conversion Rate")

    def test_no_node_still_describes_the_old_window(self):
        text = " ".join(
            f"{node.label or ''} {node.description or ''}" for node in NODES
        )
        for stale in ("6-Month", "6 months", "six months"):
            self.assertNotIn(stale, text)

    def test_every_edge_connects_declared_nodes(self):
        ids = {node.id for node in NODES}
        for edge in EDGES:
            self.assertIn(edge.source, ids)
            self.assertIn(edge.target, ids)

    def test_every_leaf_has_a_value(self):
        baseline = compute_baseline()
        values = node_values(baseline)
        for leaf in LEAF_IDS:
            self.assertIn(leaf, values, f"{leaf} has no displayed value")


class TestTransformationFlows(unittest.TestCase):
    def test_every_flow_builds(self):
        for leaf in sorted(FLOW_IDS):
            with self.subTest(leaf=leaf):
                nodes, edges = transformation_flow(leaf)
                self.assertTrue(nodes)
                self.assertTrue(edges)

    def test_an_unknown_leaf_returns_empty_lists(self):
        self.assertEqual(transformation_flow("not_a_leaf"), ([], []))
        self.assertEqual(transformation_flow(None), ([], []))

    def test_the_window_filter_is_day_based(self):
        """
        The pipeline shown must be the pipeline run. A month-based filter here
        would be describing a window the metric no longer uses.
        """
        for leaf in ("purch_cust_1", "tot_orders_1", "tot_gross_val"):
            with self.subTest(leaf=leaf):
                nodes, edges = transformation_flow(leaf)
                text = all_text(nodes, edges)
                self.assertIn("customer_age_day", text)
                self.assertIn(f"BETWEEN 0 AND {WINDOW_DAYS - 1}", text)
                self.assertNotIn("customer_age_month", text)

    def test_flows_name_the_cohort_they_describe(self):
        baseline = compute_baseline()
        nodes, edges = transformation_flow("acq_users")
        self.assertIn(baseline.cohort_label, all_text(nodes, edges))

    def test_flows_are_rebuilt_per_call(self):
        """
        Built lazily, so the cohort on the handoff link reaches them. Baking
        them in at import would pin the first participant's cohort onto
        everyone after them.
        """
        first, _ = transformation_flow("acq_users")
        second, _ = transformation_flow("acq_users")
        self.assertIsNot(first, second)

    def test_no_flow_still_describes_the_old_window(self):
        for leaf in sorted(FLOW_IDS):
            with self.subTest(leaf=leaf):
                text = all_text(*transformation_flow(leaf))
                for stale in ("six months", "6 months", "BETWEEN 1 AND 6"):
                    self.assertNotIn(stale, text)


class TestScenarioBasics(unittest.TestCase):
    def setUp(self):
        self.baseline = compute_baseline()
        self.scenario = from_baseline(self.baseline)

    def test_propagation_identities_hold(self):
        for name, passed, detail in run_scenario_checks(self.scenario):
            self.assertTrue(passed, f"{name}: {detail}")

    def test_goal_is_an_uplift_on_the_baseline(self):
        self.assertAlmostEqual(
            goal_value(self.baseline, 15),
            self.baseline.customer_value * 1.15,
            places=9,
        )

    def test_the_goal_is_a_floor_not_a_target(self):
        """
        Exceeding the goal is success. Nothing scales a scenario back down to
        land on it -- an earlier version did, which meant it could tell someone
        who had just raised conversion to 41% to set it to 36%.
        """
        goal = goal_value(self.baseline, 15)
        ambitious = Scenario(
            conversion_rate=self.baseline.conversion_rate * 1.5,
            orders_per_purchasing_customer=(
                self.baseline.orders_per_purchasing_customer
            ),
            average_order_value=self.baseline.average_order_value,
            acquired_users=self.baseline.future_acquired_users,
        )
        self.assertGreater(ambitious.customer_value, goal)
        # The scenario is reported as-is; nothing pulls it back to the goal.
        self.assertAlmostEqual(
            ambitious.customer_value,
            ambitious.conversion_rate
            * ambitious.orders_per_purchasing_customer
            * ambitious.average_order_value,
            places=9,
        )

    def test_a_scenario_never_writes_back_to_the_baseline(self):
        before = self.baseline.customer_value
        Scenario(
            conversion_rate=0.9,
            orders_per_purchasing_customer=99.0,
            average_order_value=99.0,
            acquired_users=self.baseline.future_acquired_users,
        )
        self.assertEqual(compute_baseline().customer_value, before)


class TestScenarioPropagation(unittest.TestCase):
    def setUp(self):
        self.baseline = compute_baseline()
        self.scenario = from_baseline(self.baseline)

    def test_from_baseline_reproduces_the_observed_rates(self):
        self.assertAlmostEqual(
            self.scenario.customer_value, self.baseline.customer_value, places=9
        )

    def test_scenarios_are_propagated_on_the_future_cohort(self):
        """
        Not on the cohort being explained. The simulator plans the next three
        months, so putting a 31-user group beside a 448-user one and calling
        the difference a consequence of the assumptions would be wrong.
        """
        self.assertEqual(
            self.scenario.acquired_users, self.baseline.future_acquired_users
        )
        self.assertNotEqual(
            self.baseline.future_acquired_users, self.baseline.acquired_users
        )

    def test_the_headline_does_not_depend_on_the_cohort_size(self):
        """
        Customer value is per acquired user, so the future volume divides back
        out. Only the absolute counts scale with it.
        """
        from dataclasses import replace

        doubled = replace(
            self.scenario, acquired_users=self.scenario.acquired_users * 2
        )
        self.assertAlmostEqual(
            doubled.customer_value, self.scenario.customer_value, places=9
        )
        self.assertAlmostEqual(
            doubled.total_orders, self.scenario.total_orders * 2, places=6
        )

    def test_assumptions_are_taken_exactly_as_set(self):
        """
        No tolerance band is applied anywhere. A range would be our guess at
        what counts as a plausible movement, and the simulator exists to let
        someone explore a movement we have not anticipated.
        """
        exact = Scenario(
            conversion_rate=0.6180,
            orders_per_purchasing_customer=12.345,
            average_order_value=67.89,
            acquired_users=self.baseline.future_acquired_users,
        )
        self.assertEqual(exact.conversion_rate, 0.6180)
        self.assertEqual(exact.orders_per_purchasing_customer, 12.345)
        self.assertEqual(exact.average_order_value, 67.89)
        self.assertAlmostEqual(
            exact.customer_value, 0.6180 * 12.345 * 67.89, places=9
        )

    def test_a_scenario_beyond_the_observed_range_is_allowed(self):
        """The sliders must not be capped by what the history happens to hold."""
        _, highest = self.baseline.observed_range("conversion_rate")
        beyond = Scenario(
            conversion_rate=highest * 1.5,
            orders_per_purchasing_customer=(
                self.baseline.orders_per_purchasing_customer
            ),
            average_order_value=self.baseline.average_order_value,
            acquired_users=self.baseline.future_acquired_users,
        )
        self.assertGreater(beyond.conversion_rate, highest)
        for _, passed, detail in run_scenario_checks(beyond):
            self.assertTrue(passed, detail)


class TestObservedRanges(unittest.TestCase):
    def setUp(self):
        self.baseline = compute_baseline()

    def test_each_factor_has_a_range_from_the_period(self):
        for attribute in (
            "conversion_rate",
            "orders_per_purchasing_customer",
            "average_order_value",
        ):
            with self.subTest(factor=attribute):
                low, high = self.baseline.observed_range(attribute)
                self.assertLessEqual(low, high)
                observed = [
                    getattr(point, attribute) for point in self.baseline.by_month
                ]
                self.assertEqual(low, min(observed))
                self.assertEqual(high, max(observed))

    def test_observed_best_takes_each_factor_at_its_own_maximum(self):
        conversion, orders, order_value = self.baseline.observed_best
        self.assertEqual(
            conversion, self.baseline.observed_range("conversion_rate")[1]
        )
        self.assertEqual(
            orders,
            self.baseline.observed_range("orders_per_purchasing_customer")[1],
        )
        self.assertEqual(
            order_value, self.baseline.observed_range("average_order_value")[1]
        )

    def test_observed_best_is_a_composite_not_a_real_month(self):
        """
        The three maxima can come from three different months, so the card
        showing it has to say so rather than let it read as a real quarter.
        """
        scenario = from_observed_best(self.baseline)
        matching = [
            point
            for point in self.baseline.by_month
            if point.conversion_rate == scenario.conversion_rate
            and point.orders_per_purchasing_customer
            == scenario.orders_per_purchasing_customer
            and point.average_order_value == scenario.average_order_value
        ]
        self.assertEqual(matching, [], "the composite matched a single month")

    def test_observed_best_is_at_least_as_good_as_every_month(self):
        for point in self.baseline.by_month:
            self.assertLessEqual(
                point.customer_value,
                from_observed_best(self.baseline).customer_value + 1e-9,
            )


class TestFutureAcquiredUsers(unittest.TestCase):
    def setUp(self):
        self.baseline = compute_baseline()

    def test_taken_from_the_same_months_a_year_earlier(self):
        """Cohort Jun 2024 plans Jul-Sep 2024, estimated from Jul-Sep 2023."""
        self.assertEqual(self.baseline.cohort_label, "Jun 2024")
        self.assertEqual(self.baseline.future_period_label, "Jul-Sep 2024")
        self.assertEqual(self.baseline.future_acquired_users, 448)

    def test_it_is_positive_so_a_pathway_never_divides_by_zero(self):
        self.assertGreater(self.baseline.future_acquired_users, 0)

    def test_falls_back_when_a_year_earlier_is_missing(self):
        """
        The earliest cohorts have no prior year in the data. Rather than a
        pathway divided by zero, the estimate repeats the cohort's own size.
        """
        earliest = compute_baseline(
            pd.Period("2020-07", freq="M"), pd.Period("2020-09", freq="M")
        )
        self.assertGreater(earliest.future_acquired_users, 0)


class TestSimulationDeltas(unittest.TestCase):
    def test_baseline_against_itself_moves_nothing(self):
        """With no scenario, every node shows a flat delta against itself."""
        from data.graph_data import DeltaDirection

        deltas = simulation_deltas(compute_baseline())
        for node_id, delta in deltas.items():
            with self.subTest(node=node_id):
                self.assertEqual(delta.direction, DeltaDirection.FLAT)

    def test_raising_an_assumption_moves_the_headline_up(self):
        from dataclasses import replace

        from data.graph_data import DeltaDirection

        baseline = compute_baseline()
        raised = replace(
            from_baseline(baseline),
            average_order_value=baseline.average_order_value * 1.2,
        )
        deltas = simulation_deltas(baseline, raised)
        self.assertEqual(deltas["cust_val"].direction, DeltaDirection.UP)
        self.assertEqual(deltas["avg_order_val"].direction, DeltaDirection.UP)
        # Acquisition group size is not an assumption the simulator moves.
        self.assertEqual(deltas["acq_users"].direction, DeltaDirection.FLAT)

    def test_every_provenance_leaf_gets_a_delta(self):
        deltas = simulation_deltas(compute_baseline())
        for leaf in LEAF_IDS:
            self.assertIn(leaf, deltas)


if __name__ == "__main__":
    unittest.main()
