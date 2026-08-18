"""
Tests for study condition assignment.

The two properties that matter most: resolution **fails closed** (a bad link can
never grant CLUE), and counterbalancing is exact (condition must not correlate
with order, or the study can't separate the two).
"""

import json
import tempfile
import unittest
from pathlib import Path

from study.make_sessions import build_registry, links
from study.session import DEV_PARTICIPANT, DEV_TOKENS, lookup


class TestLookup(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "sessions.json"
        self.path.write_text(json.dumps({
            "aaa111": {"participant": "P01", "block": 1, "clue": True},
            "bbb222": {"participant": "P01", "block": 2, "clue": False},
        }))

    def test_enabled_token(self):
        session = lookup("aaa111", self.path)
        self.assertTrue(session.clue_enabled)
        self.assertEqual(session.participant, "P01")
        self.assertEqual(session.block, 1)
        self.assertEqual(session.condition, "clue")
        self.assertTrue(session.is_known)

    def test_disabled_token(self):
        session = lookup("bbb222", self.path)
        self.assertFalse(session.clue_enabled)
        self.assertEqual(session.block, 2)
        self.assertEqual(session.condition, "baseline")

    def test_unknown_token_fails_closed(self):
        session = lookup("nope", self.path)
        self.assertFalse(session.clue_enabled)
        self.assertIsNone(session.participant)
        self.assertFalse(session.is_known)
        # The token is still retained so the bad link shows up in the logs.
        self.assertEqual(session.token, "nope")

    def test_missing_token_fails_closed(self):
        for token in (None, ""):
            with self.subTest(token=token):
                self.assertFalse(lookup(token, self.path).clue_enabled)

    def test_missing_registry_fails_closed(self):
        session = lookup("aaa111", Path(self.dir.name) / "absent.json")
        self.assertFalse(session.clue_enabled)

    def test_corrupt_registry_fails_closed_without_raising(self):
        broken = Path(self.dir.name) / "broken.json"
        broken.write_text("{not json")
        self.assertFalse(lookup("aaa111", broken).clue_enabled)

    def test_edited_token_cannot_escalate(self):
        """Nudging a character must not land on the other condition."""
        for edited in ("aaa112", "aaa11", "AAA111", "aaa111 "):
            with self.subTest(token=edited):
                self.assertFalse(lookup(edited, self.path).clue_enabled)


class TestDevTokens(unittest.TestCase):
    """Memorable tokens for development, which must never reach a participant."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.empty = Path(self.dir.name) / "sessions.json"
        self.empty.write_text("{}")

    def test_dev_opens_the_clue_condition(self):
        session = lookup("dev", self.empty)
        self.assertTrue(session.clue_enabled)
        self.assertTrue(session.is_dev)

    def test_dev_baseline_opens_the_control_condition(self):
        session = lookup("dev-baseline", self.empty)
        self.assertFalse(session.clue_enabled)
        self.assertTrue(session.is_dev)

    def test_dev_sessions_are_labelled_not_anonymous(self):
        """Exploratory clicks must be filterable out of the study data."""
        session = lookup("dev", self.empty)
        self.assertEqual(session.participant, DEV_PARTICIPANT)
        self.assertIsNone(session.block)

    def test_real_participants_are_never_flagged_as_dev(self):
        registry = Path(self.dir.name) / "real.json"
        registry.write_text(json.dumps(
            {"aaa111": {"participant": "P01", "block": 1, "clue": True}}
        ))
        self.assertFalse(lookup("aaa111", registry).is_dev)

    def test_dev_tokens_survive_registry_regeneration(self):
        """
        make_sessions.py rewrites sessions.json wholesale, which is why these
        live in code rather than in the registry.
        """
        for token in DEV_TOKENS:
            with self.subTest(token=token):
                self.assertTrue(lookup(token, self.empty).is_known)

    def test_dev_tokens_never_appear_in_generated_links(self):
        registry = build_registry(24, seed=11)
        self.assertFalse(set(registry) & set(DEV_TOKENS))
        for _, _, _, url in links(registry, "https://host"):
            for token in DEV_TOKENS:
                self.assertNotIn(f"s={token}", url)


class TestCounterbalancing(unittest.TestCase):
    def test_exact_half_start_with_clue(self):
        for count in (2, 8, 24):
            with self.subTest(participants=count):
                registry = build_registry(count, seed=1)
                first_clue = sum(
                    1 for e in registry.values() if e["block"] == 1 and e["clue"]
                )
                self.assertEqual(first_clue, count // 2)

    def test_every_participant_gets_both_conditions(self):
        registry = build_registry(10, seed=7)
        by_participant: dict[str, list[dict]] = {}
        for entry in registry.values():
            by_participant.setdefault(entry["participant"], []).append(entry)

        self.assertEqual(len(by_participant), 10)
        for participant, entries in by_participant.items():
            with self.subTest(participant=participant):
                self.assertEqual(sorted(e["block"] for e in entries), [1, 2])
                self.assertEqual(sorted(e["clue"] for e in entries), [False, True])

    def test_tokens_are_unique_and_opaque(self):
        registry = build_registry(24, seed=3)
        self.assertEqual(len(registry), 48)
        for token, entry in registry.items():
            # Nothing in the token may reveal the condition.
            self.assertNotIn("clue", token.lower())
            self.assertNotIn(entry["participant"].lower(), token.lower())

    def test_odd_participant_count_is_handled(self):
        registry = build_registry(5, seed=2)
        self.assertEqual(len(registry), 10)
        first_clue = sum(1 for e in registry.values() if e["block"] == 1 and e["clue"])
        self.assertEqual(first_clue, 2)  # 5 // 2

    def test_seed_makes_it_reproducible_in_assignment_not_tokens(self):
        a, b = build_registry(8, seed=99), build_registry(8, seed=99)
        order = lambda reg: sorted(  # noqa: E731
            (e["participant"], e["block"], e["clue"]) for e in reg.values()
        )
        self.assertEqual(order(a), order(b))
        self.assertNotEqual(set(a), set(b))  # tokens stay random

    def test_rejects_empty_study(self):
        with self.assertRaises(ValueError):
            build_registry(0)

    def test_links_are_well_formed(self):
        registry = build_registry(4, seed=5)
        rows = links(registry, "https://study.example.com/")
        self.assertEqual(len(rows), 8)
        for participant, block, condition, url in rows:
            self.assertIn(condition, ("CLUE", "baseline"))
            self.assertTrue(url.startswith("https://study.example.com/?s="))
            self.assertNotIn("//?", url)  # trailing slash handled
        self.assertEqual([r[0] for r in rows[:2]], ["P01", "P01"])


if __name__ == "__main__":
    unittest.main()
