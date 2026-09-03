"""
End-to-end tests for the card menu and the study condition it carries.

Drives the real app through AppTest with a session token in the query string,
which is exactly how a participant reaches it. The property under test is the
study's single manipulated variable: an Open in CLUE item appears in one
condition and not the other, and nothing else differs.
"""

# Redirect interaction logging away from the real study log before the app
# is imported or driven; see study.events.use_temporary_log_dir.
from study.events import use_temporary_log_dir

use_temporary_log_dir()

import json
import tempfile
import unittest
from pathlib import Path

APP = str(Path(__file__).resolve().parent.parent / "app.py")

CLUE_TOKEN = "aaa111"
BASELINE_TOKEN = "bbb222"

REGISTRY = {
    CLUE_TOKEN: {"participant": "P01", "block": 1, "clue": True},
    BASELINE_TOKEN: {"participant": "P01", "block": 2, "clue": False},
}


def run_app(token: str | None):
    """Start the dashboard as a participant with this token would see it."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(APP, default_timeout=180)
    if token is not None:
        app.query_params["s"] = token
    return app.run()


def install_fixtures(cls, clue_reachable: bool) -> None:
    """
    Point the registry at a fixture and pin CLUE's reachability.

    `is_clue_running` is patched on `components.kpi_cards`, not on `clue`: the
    card module imported the name directly, so rebinding it at the source would
    leave the already-bound reference untouched.
    """
    import components.kpi_cards as cards_module
    import study.session as session_module

    cls._tmp = tempfile.TemporaryDirectory()
    path = Path(cls._tmp.name) / "sessions.json"
    path.write_text(json.dumps(REGISTRY))
    cls._original_path = session_module.REGISTRY_PATH
    session_module.REGISTRY_PATH = path

    cls._original_probe = cards_module.is_clue_running
    cards_module.is_clue_running = lambda url: clue_reachable


def remove_fixtures(cls) -> None:
    import components.kpi_cards as cards_module
    import study.session as session_module

    session_module.REGISTRY_PATH = cls._original_path
    cards_module.is_clue_running = cls._original_probe
    cls._tmp.cleanup()


def menu_item_keys(app) -> set[str]:
    return {button.key for button in app.button}


def clue_links(app) -> list[str]:
    return [element.proto.url for element in app.get("link_button")]


class TestConditionGating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import streamlit.testing.v1  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"AppTest unavailable: {exc}")

        # Registry points at a fixture (the real one is gitignored), and CLUE is
        # not actually running during tests, so its reachability is pinned.
        install_fixtures(cls, clue_reachable=True)

    @classmethod
    def tearDownClass(cls):
        remove_fixtures(cls)

    def test_clue_condition_offers_the_link(self):
        app = run_app(CLUE_TOKEN)
        self.assertFalse(app.exception)
        urls = clue_links(app)
        self.assertEqual(len(urls), 1, "expected exactly one Open in CLUE link")
        self.assertIn("metric=PLTV", urls[0])
        self.assertIn(f"s={CLUE_TOKEN}", urls[0])

    def test_baseline_condition_offers_no_link(self):
        app = run_app(BASELINE_TOKEN)
        self.assertFalse(app.exception)
        self.assertEqual(clue_links(app), [])

    def test_unknown_token_fails_closed(self):
        app = run_app("garbage")
        self.assertFalse(app.exception)
        self.assertEqual(clue_links(app), [])

    def test_no_token_fails_closed(self):
        app = run_app(None)
        self.assertFalse(app.exception)
        self.assertEqual(clue_links(app), [])

    def test_only_the_clue_item_differs_between_conditions(self):
        """
        The heart of the experimental design: one variable, nothing else.

        Both conditions must present an identical dashboard apart from the CLUE
        entry point -- same cards, same menu actions, same numbers.
        """
        clue_app = run_app(CLUE_TOKEN)
        baseline_app = run_app(BASELINE_TOKEN)

        self.assertEqual(menu_item_keys(clue_app), menu_item_keys(baseline_app))

        def text(app):
            return " ".join(m.value for m in app.markdown)

        self.assertEqual(text(clue_app), text(baseline_app))


class TestMenuContents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TestConditionGating.setUpClass()
        cls.addClassCleanup(TestConditionGating.tearDownClass)
        cls.app = run_app(CLUE_TOKEN)

    def test_every_card_has_a_menu_with_both_actions(self):
        keys = menu_item_keys(self.app)
        for metric_id in (
            "customer_value", "conversion_rate", "orders_per_purchasing_customer",
            "average_order_value", "acquired_users",
        ):
            with self.subTest(metric=metric_id):
                # Metric Details was removed from the menu.
                self.assertNotIn(f"details_{metric_id}", keys)
                self.assertIn(f"underlying_{metric_id}", keys)

    def test_underlying_action_opens_that_panel_directly(self):
        app = run_app(CLUE_TOKEN)
        app.button(key="underlying_average_order_value").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["open_panel"], "underlying")
        self.assertEqual(app.session_state["metric_nav"], ["average_order_value"])

    def test_condition_is_pinned_against_url_edits(self):
        """Changing the token mid-session must not change condition."""
        app = run_app(BASELINE_TOKEN)
        app.query_params["s"] = CLUE_TOKEN
        app.run()
        self.assertEqual(clue_links(app), [])


class TestClueUnreachable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_fixtures(cls, clue_reachable=False)

    @classmethod
    def tearDownClass(cls):
        remove_fixtures(cls)

    def test_shows_a_disabled_item_instead_of_a_dead_link(self):
        app = run_app(CLUE_TOKEN)
        self.assertFalse(app.exception)
        self.assertEqual(clue_links(app), [], "should not link to a dead CLUE")
        self.assertIn("clue_down_customer_value", menu_item_keys(app))


if __name__ == "__main__":
    unittest.main()
