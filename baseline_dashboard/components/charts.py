"""
charts.py
---------
The two charts, both on the months-since-acquisition axis.

They are drawn from one tidy frame produced by `metrics.compute.chart_frame`,
so the cumulative line is always the running sum of the contribution bars --
the relationship the spec requires, enforced by construction rather than by
two parallel calculations agreeing.

Each is a single series, so neither carries a legend: the title names the one
thing plotted. Clicking a mark selects that month and scopes the
underlying-data view to it.
"""

import altair as alt
import pandas as pd
import streamlit as st

from components.styles import (
    BORDER,
    FONT,
    GRID,
    SERIES,
    SERIES_MUTED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from metrics.compute import CohortMetrics, chart_frame

CHART_HEIGHT = 300

# Panel height for the bordered container a chart sits in: the plot, plus its
# title and (two-line) subtitle, plus container padding. Fixed so both panels
# stay level regardless of how each subtitle wraps.
CHART_PANEL_HEIGHT = 425


def _heading(title: str, subtitle: str) -> None:
    st.markdown(
        f'<p class="bd-chart-title">{title}</p>'
        f'<p class="bd-chart-subtitle">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def _configure(chart: alt.Chart) -> alt.Chart:
    """Recessive axes and grid, so the data carries the emphasis."""
    return (
        chart.properties(height=CHART_HEIGHT)
        .configure_view(stroke=None)
        .configure_axis(
            labelFont=FONT,
            titleFont=FONT,
            labelColor=TEXT_SECONDARY,
            titleColor=TEXT_MUTED,
            titleFontSize=11,
            labelFontSize=11,
            titlePadding=12,
            domainColor=BORDER,
            tickColor=BORDER,
            gridColor=GRID,
        )
        .configure_text(font=FONT)
    )


def _x_axis() -> alt.X:
    return alt.X(
        "month_label:N",
        sort=alt.SortField("customer_age_month"),
        title="Months since acquisition",
        axis=alt.Axis(labelAngle=0, grid=False),
    )


def _tooltip() -> list[alt.Tooltip]:
    return [
        alt.Tooltip("month_label:N", title="Customer age"),
        alt.Tooltip("monthly_contribution:Q", title="This month", format="$,.2f"),
        alt.Tooltip("cumulative_value:Q", title="Cumulative", format="$,.2f"),
    ]


def _empty_state(message: str) -> None:
    st.markdown(
        f'<div style="height:{CHART_HEIGHT}px;display:flex;align-items:center;'
        f'justify-content:center;color:{TEXT_MUTED};font-family:{FONT};'
        f'font-size:0.9rem;text-align:center;padding:0 2rem;">{message}</div>',
        unsafe_allow_html=True,
    )


def _selected_month(key: str) -> int | None:
    """Read the age month a participant clicked, if any."""
    event = st.session_state.get(key)
    if not event:
        return None
    rows = (event.get("selection") or {}).get("pick") or []
    if not rows:
        return None
    return int(rows[0]["customer_age_month"])


# ---------------------------------------------------------------------------
# Chart 1 -- cumulative
# ---------------------------------------------------------------------------

def render_cumulative_chart(metrics: CohortMetrics) -> int | None:
    _heading(
        f"Customer Value in the First {metrics.cohort.window} Months",
        "Average cumulative value per acquired user",
    )

    if not metrics.acquired_users:
        _empty_state("No users were acquired in this reference period.")
        return None

    frame = chart_frame(metrics)
    picker = alt.selection_point(
        fields=["customer_age_month"], on="click", empty=True, name="pick"
    )

    base = alt.Chart(frame).encode(
        x=_x_axis(),
        y=alt.Y(
            "cumulative_value:Q",
            title="Cumulative value per acquired user",
            axis=alt.Axis(format="$,.0f", tickCount=6),
            scale=alt.Scale(nice=True, zero=True),
        ),
    )

    line = base.mark_line(color=SERIES, strokeWidth=2)
    points = base.mark_point(
        filled=True, size=95, color=SERIES, stroke="#FFFFFF", strokeWidth=2
    ).encode(
        opacity=alt.condition(picker, alt.value(1.0), alt.value(0.35)),
        tooltip=_tooltip(),
    ).add_params(picker)

    # Only the final point is labelled -- it is the headline number, and
    # labelling every point would clutter a line that is already monotonic.
    final = (
        alt.Chart(frame.tail(1))
        .mark_text(dy=-16, fontWeight="bold", fontSize=13, color=TEXT_PRIMARY)
        .encode(x=_x_axis(), y="cumulative_value:Q",
                text=alt.Text("cumulative_value:Q", format="$,.2f"))
    )

    st.altair_chart(
        _configure(line + points + final),
        width="stretch",
        on_select="rerun",
        key="chart_cumulative",
    )
    return _selected_month("chart_cumulative")


# ---------------------------------------------------------------------------
# Chart 2 -- monthly contribution
# ---------------------------------------------------------------------------

def render_contribution_chart(metrics: CohortMetrics) -> int | None:
    _heading(
        "Monthly Value Contribution",
        "Average additional value generated per acquired user in each month "
        "after acquisition",
    )

    if not metrics.acquired_users:
        _empty_state("No users were acquired in this reference period.")
        return None

    frame = chart_frame(metrics)
    picker = alt.selection_point(
        fields=["customer_age_month"], on="click", empty=True, name="pick"
    )

    base = alt.Chart(frame).encode(
        x=_x_axis().scale(alt.Scale(paddingInner=0.3, paddingOuter=0.2)),
        y=alt.Y(
            "monthly_contribution:Q",
            title="Value per acquired user",
            axis=alt.Axis(format="$,.0f", tickCount=6),
            scale=alt.Scale(nice=True, zero=True),
        ),
    )

    bars = base.mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=SERIES
    ).encode(
        color=alt.condition(picker, alt.value(SERIES), alt.value(SERIES_MUTED)),
        tooltip=_tooltip(),
    ).add_params(picker)

    # Every bar is labelled: there are at most 12, and the study task asks
    # participants to check that these sum to the headline by hand.
    labels = base.mark_text(dy=-9, fontSize=11, color=TEXT_SECONDARY).encode(
        text=alt.Text("monthly_contribution:Q", format="$,.2f")
    )

    st.altair_chart(
        _configure(bars + labels),
        width="stretch",
        on_select="rerun",
        key="chart_contribution",
    )
    return _selected_month("chart_contribution")


def month_summary(metrics: CohortMetrics, age_month: int) -> pd.DataFrame:
    """Summary row for a selected chart month (spec's per-month drilldown)."""
    return pd.DataFrame(
        {
            "Customer Age": [f"Month {age_month}"],
            "Monthly Contribution": [metrics.monthly_contribution[age_month]],
            "Cumulative Value": [metrics.cumulative_value[age_month]],
        }
    )
