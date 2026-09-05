"""Tests for the CLUE link module and its metric mapping."""

import os
import unittest
from unittest import mock

import pandas as pd

from clue import DEFAULT_CLUE_URL, base_url, clue_url_for
from metrics.compute import CohortFilter
from metrics.registry import CARD_IDS, METRICS
from study.session import Session

COHORT = CohortFilter(pd.Period("2024-01", freq="M"), pd.Period("2024-06", freq="M"))

ENABLED = Session(token="tok123", participant="P01", block=1, clue_enabled=True)
ANON = Session(token=None, participant=None, block=None, clue_enabled=False)


class TestBaseUrl(unittest.TestCase):
    def test_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(base_url(), DEFAULT_CLUE_URL)

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"CLUE_URL": "https://clue.example.com/"}):
            self.assertEqual(base_url(), "https://clue.example.com")


class TestClueUrlFor(unittest.TestCase):
    def test_primary_metric_carries_name_period_and_token(self):
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ENABLED, COHORT)
        self.assertEqual(
            url,
            "http://host:8502/?metric=90-Day+Customer+Value"
            "&start=2024-01&end=2024-06&s=tok123",
        )

    def test_token_omitted_when_absent(self):
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ANON, COHORT)
        self.assertEqual(
            url,
            "http://host:8502/?metric=90-Day+Customer+Value"
            "&start=2024-01&end=2024-06",
        )

    def test_period_omitted_when_no_cohort_given(self):
        """CLUE falls back to its own default, which matches the dashboard's."""
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ANON)
        self.assertEqual(url, "http://host:8502/?metric=90-Day+Customer+Value")

    def test_the_period_follows_the_filter(self):
        narrowed = CohortFilter(
            pd.Period("2022-01", freq="M"), pd.Period("2022-03", freq="M")
        )
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ANON, narrowed)
        self.assertIn("start=2022-01&end=2022-03", url)

    def test_session_is_optional(self):
        self.assertIsNotNone(clue_url_for("customer_value"))

    def test_only_the_primary_card_is_mapped(self):
        """The other four cards have no CLUE counterpart yet."""
        mapped = [mid for mid in CARD_IDS if METRICS[mid].clue_metric]
        self.assertEqual(mapped, ["customer_value"])

        for metric_id in CARD_IDS:
            if metric_id == "customer_value":
                continue
            with self.subTest(metric=metric_id):
                self.assertIsNone(clue_url_for(metric_id, ENABLED, COHORT))

    def test_unknown_metric_returns_none(self):
        self.assertIsNone(clue_url_for("not_a_metric", ENABLED, COHORT))

    def test_component_metrics_are_unmapped(self):
        for metric_id in ("total_orders", "gross_value", "purchasing_customers"):
            with self.subTest(metric=metric_id):
                self.assertIsNone(clue_url_for(metric_id, ENABLED, COHORT))


if __name__ == "__main__":
    unittest.main()
