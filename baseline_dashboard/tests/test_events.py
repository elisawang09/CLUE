"""Tests for interaction logging."""

import json
import tempfile
import unittest
from pathlib import Path

from study.events import (
    JsonlFileSink,
    build_event,
    get_sink,
    log_event,
    set_sink,
)
from study.session import Session

SESSION = Session(token="tok123", participant="P07", block=2, clue_enabled=True)


class CollectingSink:
    def __init__(self):
        self.events = []

    def write(self, event):
        self.events.append(event)


class ExplodingSink:
    def write(self, event):
        raise OSError("disk full")


class TestEventShape(unittest.TestCase):
    def test_carries_session_context(self):
        event = build_event("open_details", SESSION, metric="customer_value")
        self.assertEqual(event["action"], "open_details")
        self.assertEqual(event["participant"], "P07")
        self.assertEqual(event["block"], 2)
        self.assertEqual(event["condition"], "clue")
        self.assertEqual(event["token"], "tok123")
        self.assertEqual(event["metric"], "customer_value")
        self.assertIn("timestamp", event)

    def test_anonymous_session_records_baseline(self):
        anon = Session(token=None, participant=None, block=None, clue_enabled=False)
        event = build_event("session_start", anon)
        self.assertEqual(event["condition"], "baseline")
        self.assertIsNone(event["participant"])

    def test_event_is_json_serializable(self):
        event = build_event("csv_export", SESSION, rows=1234)
        self.assertIn('"rows": 1234', json.dumps(event, default=str))


class TestSinks(unittest.TestCase):
    def setUp(self):
        # Restore whatever was here (the package-level temp sink), not a fresh
        # default -- a default would point back at the real study log and every
        # later test would write into it.
        self.addCleanup(set_sink, get_sink())

    def test_events_reach_the_sink(self):
        sink = CollectingSink()
        set_sink(sink)
        log_event("open_underlying", SESSION, metric="average_order_value")
        self.assertEqual(len(sink.events), 1)
        self.assertEqual(sink.events[0]["metric"], "average_order_value")

    def test_a_failing_sink_never_breaks_the_dashboard(self):
        """Losing a log line is bad; crashing in front of a participant is worse."""
        set_sink(ExplodingSink())
        event = log_event("open_details", SESSION)
        self.assertEqual(event["action"], "open_details")

    def test_file_sink_writes_one_json_object_per_line(self):
        with tempfile.TemporaryDirectory() as directory:
            sink = JsonlFileSink(Path(directory))
            set_sink(sink)
            log_event("session_start", SESSION)
            log_event("csv_export", SESSION, rows=10)

            files = list(Path(directory).glob("events-*.jsonl"))
            self.assertEqual(len(files), 1)
            lines = files[0].read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(
                [json.loads(line)["action"] for line in lines],
                ["session_start", "csv_export"],
            )

    def test_file_sink_creates_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "logs"
            set_sink(JsonlFileSink(target))
            log_event("session_start", SESSION)
            self.assertTrue(list(target.glob("events-*.jsonl")))

    def test_appends_rather_than_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            set_sink(JsonlFileSink(Path(directory)))
            for i in range(5):
                log_event("chart_select", SESSION, age_month=i)
            path = next(Path(directory).glob("events-*.jsonl"))
            self.assertEqual(len(path.read_text().strip().splitlines()), 5)


if __name__ == "__main__":
    unittest.main()
