"""
session.py
----------
Resolves which study condition a browser session is in.

The study is within-subjects: every participant uses the dashboard both with
CLUE available and without, in a counterbalanced order. One deployment serves
both, so the condition cannot be a process-level switch — it travels in the
link, as an opaque token:

    https://<host>/?s=a7k2   ->  P01, block 1, CLUE enabled
    https://<host>/?s=m9x4   ->  P01, block 2, CLUE disabled

The token is opaque rather than a readable `?clue=on` so nothing in the address
bar tells a participant which condition they are in. A visible flag would be a
demand characteristic even in a moderated session.

Resolution **fails closed**: a missing, unknown, or edited token yields the
disabled condition. A broken link should degrade to the control condition, not
silently hand someone CLUE and corrupt a data point without anyone noticing.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

REGISTRY_PATH = Path(__file__).resolve().parent / "sessions.json"

# Query parameter carrying the session token.
TOKEN_PARAM = "s"

# Memorable tokens for development and demos, mapping to the condition they
# open. Defined here rather than in sessions.json for two reasons: regenerating
# the registry would otherwise wipe them, and they must never appear in a
# participant run sheet.
#
# They resolve under the participant id "DEV", so exploratory clicks are
# unmistakable in the logs and can never be mistaken for a real participant.
DEV_PARTICIPANT = "DEV"
DEV_TOKENS: dict[str, bool] = {
    "dev": True,            # CLUE enabled
    "dev-baseline": False,  # control, for comparing the two side by side
}

_STATE_KEY = "_study_session"


@dataclass(frozen=True)
class Session:
    """Who this browser session belongs to, and what they can see."""

    token: str | None
    participant: str | None
    block: int | None
    clue_enabled: bool

    @property
    def condition(self) -> str:
        return "clue" if self.clue_enabled else "baseline"

    @property
    def is_known(self) -> bool:
        """False when no valid token was supplied — useful for logging."""
        return self.participant is not None

    @property
    def is_dev(self) -> bool:
        """True for a development token, so analysis can drop these rows."""
        return self.participant == DEV_PARTICIPANT


ANONYMOUS = Session(token=None, participant=None, block=None, clue_enabled=False)


@st.cache_data(show_spinner=False)
def _load_registry(path: str) -> dict[str, dict]:
    """
    Token -> assignment mapping.

    Keyed by path so pointing at a different registry (tests, a second study)
    doesn't serve a stale cache.

    A missing registry is not an error: it means nobody has generated session
    links yet, and every visitor is simply anonymous (control condition).
    """
    registry = Path(path)
    if not registry.exists():
        return {}
    try:
        return json.loads(registry.read_text())
    except json.JSONDecodeError:
        # A corrupt registry must not take the dashboard down mid-session; every
        # visitor falls back to the control condition instead.
        return {}


def lookup(token: str | None, registry_path: Path | None = None) -> Session:
    """Resolve a token without touching Streamlit state. Fails closed."""
    if not token:
        return ANONYMOUS

    # Checked ahead of the registry so a regenerated sessions.json can never
    # shadow or remove a dev token.
    if token in DEV_TOKENS:
        return Session(
            token=token,
            participant=DEV_PARTICIPANT,
            block=None,
            clue_enabled=DEV_TOKENS[token],
        )

    entry = _load_registry(str(registry_path or REGISTRY_PATH)).get(token)
    if not entry:
        return Session(token=token, participant=None, block=None, clue_enabled=False)

    return Session(
        token=token,
        participant=entry.get("participant"),
        block=entry.get("block"),
        clue_enabled=bool(entry.get("clue", False)),
    )


def resolve_session() -> Session:
    """
    The session for this browser tab, resolved once and remembered.

    Pinned in session state so a participant cannot change condition mid-task by
    editing the URL: the first resolution is the one that counts.
    """
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = lookup(st.query_params.get(TOKEN_PARAM))
    return st.session_state[_STATE_KEY]
