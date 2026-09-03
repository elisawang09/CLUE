"""
filters.py
----------
The dashboard's one filter: the reference acquisition period.

It decides *which users are included*. How long each one is watched is no
longer a control -- the observation window is fixed at 90 days from each user's
own acquisition date, so the metric names never drift from the numbers.
"""

import pandas as pd
import streamlit as st

from metrics.compute import WINDOW_DAYS, CohortFilter

# The most recent year in the data, stopping at June.
#
# Acquisitions run to 2024-07, but that month is a 3-user stub at the edge of
# the data -- and the cards report the *latest* month in the range, so opening
# on it would rest the whole headline on a single purchaser. June is the last
# month with a cohort big enough to read.
DEFAULT_START = pd.Period("2024-01", freq="M")
DEFAULT_END = pd.Period("2024-06", freq="M")


def _index_of(months: pd.PeriodIndex, target: pd.Period, fallback: int) -> int:
    matches = months.get_indexer([target])
    return int(matches[0]) if matches[0] != -1 else fallback


def render_filters(months: pd.PeriodIndex) -> CohortFilter:
    """Draw the filter row and return the resulting cohort selection."""
    labels = [month.strftime("%b %Y") for month in months]

    with st.container(border=True, key="filter_bar"):
        left, spacer = st.columns([2.4, 3.6])

        with left:
            st.markdown(
                '<p class="bd-kpi-label">Reference Acquisition Period</p>',
                unsafe_allow_html=True,
            )
            from_col, to_col = st.columns(2)
            start_i = from_col.selectbox(
                "From",
                range(len(months)),
                index=_index_of(months, DEFAULT_START, 0),
                format_func=lambda i: labels[i],
                key="filter_start",
            )
            end_i = to_col.selectbox(
                "To",
                range(len(months)),
                index=_index_of(months, DEFAULT_END, len(months) - 1),
                format_func=lambda i: labels[i],
                key="filter_end",
            )

        with spacer:
            st.markdown(
                '<p class="bd-kpi-label">&nbsp;</p>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Users are included by acquisition date, then observed for "
                f"their own first {WINDOW_DAYS} days, so everyone gets an "
                "equal-length window. Cards show the most recent acquisition "
                "month in the range; charts show every month in it."
            )

    if start_i > end_i:
        st.warning(
            f"Acquisition period starts after it ends ({labels[start_i]} → "
            f"{labels[end_i]}); showing {labels[end_i]} → {labels[start_i]} instead."
        )
        start_i, end_i = end_i, start_i

    return CohortFilter(months[start_i], months[end_i])
