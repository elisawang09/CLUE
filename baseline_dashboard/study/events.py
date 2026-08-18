"""
events.py
---------
Interaction logging for study analysis.

One JSONL line per interaction, appended to `logs/events-YYYY-MM-DD.jsonl`.
Each line carries who did it (participant, block, condition), what they did, and
when — enough to reconstruct a session afterwards.

Two things this deliberately gets right:

*Only real interactions are logged.* Streamlit re-executes the whole script on
every widget change, so anything logged on the render path would produce
thousands of duplicate lines. Calls live inside click handlers and
changed-value comparisons instead.

*Writing is behind an interface.* The file sink is right for a VM you control;
a hosted platform with an ephemeral disk would silently lose the study data, and
swapping in another sink should not mean touching every call site.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import streamlit as st

from study.session import Session, resolve_session

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# Redirects the log elsewhere. Tests set this so a suite run never appends
# synthetic events to real study data.
LOG_DIR_ENV = "BASELINE_LOG_DIR"

_SEEN_KEY = "_study_logged_start"
_lock = threading.Lock()


class EventSink(Protocol):
    """Somewhere events go. Implement this to log elsewhere."""

    def write(self, event: dict) -> None: ...


class JsonlFileSink:
    """Append one JSON object per line, a file per day."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory

    @property
    def directory(self) -> Path:
        """
        Resolved at write time, not construction.

        The module-level sink is built at import, long before a test suite can
        intervene, so the override has to be read late for it to take effect.
        """
        if self._directory is not None:
            return self._directory
        override = os.environ.get(LOG_DIR_ENV)
        return Path(override) if override else LOG_DIR

    def write(self, event: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.directory / f"events-{day}.jsonl"
        line = json.dumps(event, default=str)
        # Streamlit serves sessions from a thread pool, so appends are locked.
        with _lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


_sink: EventSink = JsonlFileSink()


def set_sink(sink: EventSink) -> None:
    """Replace the destination (tests, or a non-file sink later)."""
    global _sink
    _sink = sink


def get_sink() -> EventSink:
    """The current destination, so a caller can restore it after swapping."""
    return _sink


def use_temporary_log_dir() -> str:
    """
    Point logging at a throwaway directory for the rest of the process.

    Called by the test suite: running it drives the real app, and without this
    every run would append synthetic events to real study data. Idempotent, and
    a no-op if the override is already set.
    """
    import atexit
    import tempfile

    existing = os.environ.get(LOG_DIR_ENV)
    if existing:
        return existing

    tmp = tempfile.TemporaryDirectory(prefix="baseline-test-logs-")
    os.environ[LOG_DIR_ENV] = tmp.name
    atexit.register(tmp.cleanup)
    return tmp.name


def build_event(action: str, session: Session, **fields) -> dict:
    """The record written for one interaction."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "participant": session.participant,
        "block": session.block,
        "condition": session.condition,
        "token": session.token,
        **fields,
    }


def log_event(action: str, session: Session | None = None, **fields) -> dict:
    """
    Record one interaction.

    Never raises: losing a log line is bad, but taking the dashboard down in
    front of a participant is worse.
    """
    session = session or resolve_session()
    event = build_event(action, session, **fields)
    try:
        _sink.write(event)
    except OSError:
        pass
    return event


def log_session_start(session: Session) -> None:
    """Log the first page load of a browser session, exactly once."""
    if st.session_state.get(_SEEN_KEY):
        return
    st.session_state[_SEEN_KEY] = True
    log_event("session_start", session, known_token=session.is_known)


def log_if_changed(action: str, state_key: str, value, session: Session, **fields) -> None:
    """
    Log a widget change only when the value actually differs.

    Filters re-report their value on every rerun; without this, a single
    selection would be logged once per interaction anywhere on the page.
    """
    if st.session_state.get(state_key) == value:
        return
    st.session_state[state_key] = value
    log_event(action, session, value=value, **fields)
