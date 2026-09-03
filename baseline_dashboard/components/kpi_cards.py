"""
kpi_cards.py
------------
The five headline cards, each with a ⋯ menu holding its interactions.

Each card reports the *most recent acquisition month* in the reference period,
compared against the month before it. That comparison is between two cohorts
observed the same way -- each over its own first 90 days -- which is what makes
it meaningful; a calendar-time sparkline over a window-based metric would imply
a trend the number does not have.

The comparison month is the one immediately preceding in the data, not in the
selection, so narrowing the filter to a single month still shows a change.

The menu is where the study's one manipulated variable lives. In the
CLUE-enabled condition a mapped metric gains an "Open in CLUE" item; everything
else about the dashboard is identical across conditions.
"""

from html import escape

import streamlit as st

from clue import base_url, clue_url_for, is_clue_running
from metrics.compute import CohortMetrics
from metrics.registry import (
    CARD_IDS,
    METRICS,
    PRIMARY_ID,
    formatted_value,
    percent,
)
from study.session import Session

# What a card menu click asks the app to do. Only one panel remains: the
# calculation drill-down was removed from the menu, and with it the only way in.
ACTION_UNDERLYING = "underlying"

# Fixed so all five cards match regardless of how far their titles wrap --
# titles run from one line ("Acquired Users") to three ("Orders per Purchasing
# Customer"), which otherwise leaves the row visibly ragged. Tall enough for the
# delta line, which is reserved even when there is no previous month.
# The primary card carries its emphasis through a larger value font rather than
# extra width, so the row stays an even five-column grid.
CARD_HEIGHT = 218

# Which attribute of a MonthMetrics each card compares against last month.
DELTA_ATTRIBUTES: dict[str, str] = {
    "customer_value": "customer_value",
    "conversion_rate": "conversion_rate",
    "orders_per_purchasing_customer": "orders_per_purchasing_customer",
    "average_order_value": "average_order_value",
    "acquired_users": "acquired_users",
}


def _format_delta(metric_id: str, change: float) -> str:
    """
    The change itself, in the metric's own units.

    Rates are shown in percentage *points* rather than as a percentage of a
    percentage, which is the reading people actually want and the one that
    cannot be misread as a relative change.
    """
    metric = METRICS[metric_id]
    if metric.fmt is percent:
        return f"{abs(change) * 100:,.1f} pts"
    return metric.fmt(abs(change))


def _delta_html(metric_id: str, metrics: CohortMetrics) -> str:
    """
    One card's comparison against the previous acquisition month.

    Renders an empty (but space-reserving) line when there is no previous month
    -- the earliest cohort in the data has nothing to compare against, and a
    delta of zero there would be a fabricated number rather than a missing one.
    """
    if metrics.previous is None:
        return '<div class="bd-kpi-delta">&nbsp;</div>'

    attribute = DELTA_ATTRIBUTES[metric_id]
    change = metrics.delta(attribute)
    if change is None:
        return '<div class="bd-kpi-delta">&nbsp;</div>'

    ratio = metrics.delta_ratio(attribute)
    if change > 0:
        direction, arrow = "is-up", "▲"
    elif change < 0:
        direction, arrow = "is-down", "▼"
    else:
        direction, arrow = "is-flat", "—"

    relative = f" ({abs(ratio):.1%})" if ratio is not None else ""
    context = escape(f"vs {metrics.previous.label}")
    return (
        f'<div class="bd-kpi-delta {direction}">'
        f"{arrow} {_format_delta(metric_id, change)}{relative} "
        f'<span class="bd-delta-context">{context}</span>'
        f"</div>"
    )


def _card_body(metric_id: str, metrics: CohortMetrics) -> str:
    """
    The cohort month, the value, its unit, and the change against last month.

    The month is named on every card rather than left to the filter above: the
    cards report the latest month in the reference period, not the period
    itself, so a card carrying only a value would invite reconciling it against
    the wrong cohort.
    """
    metric = METRICS[metric_id]
    is_primary = metric_id == PRIMARY_ID
    return f"""
        <div class="bd-kpi-month">{escape(metrics.latest.label)}</div>
        <div class="bd-kpi-value{' is-primary' if is_primary else ''}">
          {formatted_value(metric_id, metrics)}
        </div>
        <div class="bd-kpi-unit">{metric.unit or "&nbsp;"}</div>
        {_delta_html(metric_id, metrics)}
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
