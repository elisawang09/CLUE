"""Tests for the CLUE link module and its metric mapping."""

import os
import unittest
from unittest import mock

from clue import DEFAULT_CLUE_URL, base_url, clue_url_for
from metrics.registry import CARD_IDS, METRICS
from study.session import Session

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
    def test_primary_metric_maps_to_pltv(self):
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ENABLED)
        self.assertEqual(url, "http://host:8502/?metric=PLTV&s=tok123")

    def test_token_omitted_when_absent(self):
        with mock.patch.dict(os.environ, {"CLUE_URL": "http://host:8502"}):
            url = clue_url_for("customer_value", ANON)
        self.assertEqual(url, "http://host:8502/?metric=PLTV")

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
                self.assertIsNone(clue_url_for(metric_id, ENABLED))

    def test_unknown_metric_returns_none(self):
        self.assertIsNone(clue_url_for("not_a_metric", ENABLED))

    def test_component_metrics_are_unmapped(self):
        for metric_id in ("total_orders", "gross_value", "purchasing_customers"):
            with self.subTest(metric=metric_id):
                self.assertIsNone(clue_url_for(metric_id, ENABLED))


if __name__ == "__main__":
    unittest.main()
