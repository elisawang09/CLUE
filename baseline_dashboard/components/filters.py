"""
filters.py
----------
The dashboard's two filters.

They answer different questions and are deliberately separate controls:
the reference acquisition period decides *which users are included*, and the
observation window decides *how long each one is watched after their own
acquisition date*.
"""

import pandas as pd
import streamlit as st

from metrics.compute import DEFAULT_WINDOW, WINDOW_CHOICES, CohortFilter

# Chosen from the build's cohort report: the largest 3-month acquisition window
# in the data, so every KPI opens on a well-populated cohort.
DEFAULT_START = pd.Period("2022-01", freq="M")
DEFAULT_END = pd.Period("2022-03", freq="M")


def _index_of(months: pd.PeriodIndex, target: pd.Period, fallback: int) -> int:
    matches = months.get_indexer([target])
    return int(matches[0]) if matches[0] != -1 else fallback


def render_filters(months: pd.PeriodIndex) -> CohortFilter:
    """Draw the filter row and return the resulting cohort selection."""
    labels = [month.strftime("%b %Y") for month in months]

    with st.container(border=True, key="filter_bar"):
        left, right, spacer = st.columns([2.4, 1.3, 2.3])

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

        with right:
            st.markdown(
                '<p class="bd-kpi-label">Observation Window</p>',
                unsafe_allow_html=True,
            )
            window = st.selectbox(
                "Months after acquisition",
                WINDOW_CHOICES,
                index=WINDOW_CHOICES.index(DEFAULT_WINDOW),
                format_func=lambda w: f"First {w} months",
                key="filter_window",
            )

        with spacer:
            st.markdown(
                '<p class="bd-kpi-label">&nbsp;</p>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Users are included by acquisition date. Each is then observed "
                f"for their own first {window} months, so everyone in the cohort "
                "gets an equal-length window."
            )

    if start_i > end_i:
        st.warning(
            f"Acquisition period starts after it ends ({labels[start_i]} → "
            f"{labels[end_i]}); showing {labels[end_i]} → {labels[start_i]} instead."
        )
        start_i, end_i = end_i, start_i

    return CohortFilter(months[start_i], months[end_i], window=window)
