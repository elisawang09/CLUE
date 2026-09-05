"""
clue.py
-------
The one module that knows the CLUE app exists.

CLUE is a separate Streamlit app (the treatment condition) reached by URL, never
by import — the two apps share no code, which is what keeps the control
condition honest. Everything coupling them lives here and in one field on
MetricDef.
"""

import os
import socket
from urllib.parse import urlencode, urlparse

import streamlit as st

from metrics.compute import CohortFilter
from metrics.registry import METRICS
from study.session import TOKEN_PARAM, Session

DEFAULT_CLUE_URL = "http://localhost:8502"

# Probe timeout for the reachability check. Long enough for a local or
# same-host service, short enough that a dead CLUE never stalls a render.
PROBE_TIMEOUT_SECONDS = 0.2


def base_url() -> str:
    """Where CLUE is served. Set CLUE_URL when it isn't on the default port."""
    return os.environ.get("CLUE_URL", DEFAULT_CLUE_URL).rstrip("/")


def clue_url_for(
    metric_id: str,
    session: Session | None = None,
    cohort: CohortFilter | None = None,
) -> str | None:
    """
    Link into CLUE for a metric, or None if it has no counterpart there yet.

    Carries three things:

    - the metric name, so the handoff is self-describing;
    - the reference acquisition period, so CLUE explains the cohort the
      participant was actually looking at rather than a pinned default -- both
      apps then apply the same rule for which month the headline describes;
    - the session token, so CLUE-side logging can attribute events to the same
      participant without asking them to identify themselves twice.
    """
    metric = METRICS.get(metric_id)
    if metric is None or not metric.clue_metric:
        return None

    params = {"metric": metric.clue_metric}
    if cohort is not None:
        params["start"] = str(cohort.start_month)
        params["end"] = str(cohort.end_month)
    if session is not None and session.token:
        params[TOKEN_PARAM] = session.token
    return f"{base_url()}/?{urlencode(params)}"


@st.cache_data(ttl=30, show_spinner=False)
def is_clue_running(url: str) -> bool:
    """
    Whether CLUE is accepting connections.

    Cached for 30s so a participant clicking around never pays for the probe. A
    disabled menu item with an explanation beats a link into a browser error
    page mid-task.
    """
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False
