"""
kpi_cards.py
------------
The five headline cards, each with a ⋯ menu holding its interactions.

No sparklines and no period-over-period deltas: the metric describes one
acquisition cohort observed over its own first months, so a calendar-time
sparkline would imply a trend the number doesn't have. Each card instead
carries the cohort it belongs to, which is the context that actually matters.

The menu is where the study's one manipulated variable lives. In the
CLUE-enabled condition a mapped metric gains an "Open in CLUE" item; everything
else about the dashboard is identical across conditions.
"""

from html import escape

import streamlit as st

from clue import base_url, clue_url_for, is_clue_running
from metrics.compute import CohortMetrics
from metrics.registry import CARD_IDS, METRICS, PRIMARY_ID, formatted_value
from study.session import Session

# What a card menu click asks the app to do.
ACTION_DETAILS = "details"
ACTION_UNDERLYING = "underlying"

# Fixed so all five cards match regardless of how far their titles wrap --
# titles run from one line ("Acquired Users") to three ("Orders per Purchasing
# Customer"), which otherwise leaves the row visibly ragged.
# The primary card carries its emphasis through a larger value font rather than
# extra width, so the row stays an even five-column grid.
CARD_HEIGHT = 172


def _card_body(metric_id: str, metrics: CohortMetrics) -> str:
    """
    Value and unit only.

    The cohort is stated by the filter directly above and again in the footer,
    so repeating it on all five cards was noise.
    """
    metric = METRICS[metric_id]
    is_primary = metric_id == PRIMARY_ID
    return f"""
        <div class="bd-kpi-value{' is-primary' if is_primary else ''}">
          {formatted_value(metric_id, metrics)}
        </div>
        <div class="bd-kpi-unit">{metric.unit or "&nbsp;"}</div>
    """


def _card_title(metric_id: str, metrics: CohortMetrics) -> str:
    """
    Card title, carrying its metric description as a hover hint.

    A native `title` attribute rather than a CSS tooltip: the card is a
    fixed-height Streamlit container, which clips its own overflow, so a
    positioned pseudo-element would be cut off at the card edge. The browser
    renders this one above the page entirely.
    """
    metric = METRICS[metric_id]
    return (
        f'<p class="bd-kpi-label" title="'
        f'{escape(metric.description(metrics), quote=True)}">'
        f"{metric.name(metrics)}</p>"
    )


def _render_menu(
    metric_id: str,
    metrics: CohortMetrics,
    session: Session,
) -> str | None:
    """Draw one card's ⋯ menu. Returns the action chosen, if any."""
    chosen: str | None = None

    with st.popover("", icon=":material/more_horiz:", key=f"menu_{metric_id}"):
        if st.button(
            "Metric Details",
            key=f"details_{metric_id}",
            type="tertiary",
            width="stretch",
        ):
            chosen = ACTION_DETAILS

        if st.button(
            "View Underlying Data",
            key=f"underlying_{metric_id}",
            type="tertiary",
            width="stretch",
        ):
            chosen = ACTION_UNDERLYING

        # The manipulated variable: present only in the CLUE condition, and only
        # for metrics that have a counterpart over there.
        if session.clue_enabled:
            url = clue_url_for(metric_id, session)
            if url and is_clue_running(base_url()):
                st.link_button("Open in CLUE ↗", url, width="stretch")
            elif url:
                st.button(
                    "Open in CLUE ↗",
                    key=f"clue_down_{metric_id}",
                    type="tertiary",
                    width="stretch",
                    disabled=True,
                    help="CLUE is not reachable right now.",
                )

    return chosen


def render_kpi_cards(
    metrics: CohortMetrics,
    selected: str | None,
    session: Session,
) -> tuple[str | None, str | None]:
    """
    Draw the cards. Returns (metric_id, action) when a menu item was chosen.

    The primary card is given more width so the study's target metric reads as
    the headline rather than one of five equals.
    """
    opened: tuple[str | None, str | None] = (None, None)
    columns = st.columns(5, gap="small")

    for column, metric_id in zip(columns, CARD_IDS):
        with column, st.container(border=True, height=CARD_HEIGHT,
                                  key=f"kpi_{metric_id}"):
            # The menu only needs room for a single icon; the rest goes to the
            # title, which is tight now that all five cards share a width.
            label_col, menu_col = st.columns([6, 1], vertical_alignment="top")
            label_col.markdown(
                _card_title(metric_id, metrics), unsafe_allow_html=True
            )
            with menu_col:
                action = _render_menu(metric_id, metrics, session)

            st.markdown(_card_body(metric_id, metrics), unsafe_allow_html=True)

            if action:
                opened = (metric_id, action)

    return opened
