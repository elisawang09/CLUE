"""
charts.py
---------
The two charts, both on the acquisition-month axis.

They are drawn from one tidy frame produced by `metrics.compute.chart_frame`,
which is the same per-month table the KPI cards read. A bar and a card
reporting the same month therefore cannot disagree -- the relationship is
enforced by construction rather than by two calculations happening to agree.

Each is a single series, so neither carries a legend: the title names the one
thing plotted. The month the cards report is drawn in the accent colour and
every other month is muted, which is the only thing on screen connecting the
cards to the bars. Clicking a bar selects that acquisition month and scopes the
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
    TEXT_SECONDARY,
)
from metrics.compute import CohortMetrics, chart_frame

CHART_HEIGHT = 300

# Panel height for the bordered container a chart sits in: the plot, plus its
# title and (two-line) subtitle, plus container padding. Fixed so both panels
# stay level regardless of how each subtitle wraps.
CHART_PANEL_HEIGHT = 425

# Above this many months, per-bar value labels collide and the axis labels stop
# fitting horizontally. The reference period can span the whole dataset, so
# both have to degrade rather than overlap.
MAX_LABELLED_MONTHS = 12
MAX_HORIZONTAL_AXIS_MONTHS = 12


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


def _x_axis(frame: pd.DataFrame) -> alt.X:
    """Acquisition month, oldest to newest, angled once the labels stop fitting."""
    angle = 0 if len(frame) <= MAX_HORIZONTAL_AXIS_MONTHS else -45
    return alt.X(
        "month_label:N",
        sort=alt.SortField("sort_key"),
        title="User Acquisition Month",
        axis=alt.Axis(labelAngle=angle, grid=False),
        scale=alt.Scale(paddingInner=0.25, paddingOuter=0.15),
    )


def _tooltip(value_field: str, value_title: str, value_format: str) -> list[alt.Tooltip]:
    return [
        alt.Tooltip("month_label:N", title="User Acquisition Month"),
        alt.Tooltip(f"{value_field}:Q", title=value_title, format=value_format),
        alt.Tooltip("acquired_users:Q", title="Acquired users", format=","),
        alt.Tooltip("purchasing_customers:Q", title="Purchasing customers",
                    format=","),
    ]


def _empty_state(message: str) -> None:
    st.markdown(
        f'<div style="height:{CHART_HEIGHT}px;display:flex;align-items:center;'
        f'justify-content:center;color:{TEXT_MUTED};font-family:{FONT};'
        f'font-size:0.9rem;text-align:center;padding:0 2rem;">{message}</div>',
        unsafe_allow_html=True,
    )


def _selected_month(key: str) -> str | None:
    """Read the acquisition month a participant clicked, if any."""
    event = st.session_state.get(key)
    if not event:
        return None
    rows = (event.get("selection") or {}).get("pick") or []
    if not rows:
        return None
    return str(rows[0]["month_label"])


def _column_chart(
    metrics: CohortMetrics,
    key: str,
    value_field: str,
    value_title: str,
    axis_format: str,
    label_format: str,
    tooltip_title: str,
) -> str | None:
    """
    One vertical column chart over acquisition months.

    Both charts differ only in which column they plot and how it is formatted,
    so they share this body rather than duplicating the encoding twice and
    drifting apart.
    """
    frame = chart_frame(metrics)
    picker = alt.selection_point(
        fields=["month_label"], on="click", empty=True, name="pick"
    )

    base = alt.Chart(frame).encode(
        x=_x_axis(frame),
        y=alt.Y(
            f"{value_field}:Q",
            title=value_title,
            axis=alt.Axis(format=axis_format, tickCount=6),
            scale=alt.Scale(nice=True, zero=True),
        ),
    )

    # The month the KPI cards report is the one in full colour. A click
    # overrides that emphasis, so the selection is always visible too.
    bars = base.mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4
    ).encode(
        # Emphasis is a scale over `is_latest` rather than a nested condition:
        # Altair rejects a condition inside a condition, and a two-point scale
        # says the same thing. Clicking mutes everything the click excluded.
        color=alt.condition(
            picker,
            alt.Color(
                "is_latest:N",
                scale=alt.Scale(
                    domain=[False, True], range=[SERIES_MUTED, SERIES]
                ),
                legend=None,
            ),
            alt.value(SERIES_MUTED),
        ),
        tooltip=_tooltip(value_field, tooltip_title, label_format),
    ).add_params(picker)

    layers = bars
    if len(frame) <= MAX_LABELLED_MONTHS:
        layers = bars + base.mark_text(
            dy=-9, fontSize=11, color=TEXT_SECONDARY
        ).encode(text=alt.Text(f"{value_field}:Q", format=label_format))

    st.altair_chart(
        _configure(layers), width="stretch", on_select="rerun", key=key
    )
    return _selected_month(key)


# ---------------------------------------------------------------------------
# Chart 1 -- customer value by acquisition month
# ---------------------------------------------------------------------------

def render_customer_value_chart(metrics: CohortMetrics) -> str | None:
    _heading(
        f"{metrics.window_label} Customer Value by Acquisition Month",
        "Average value per acquired user in their first "
        f"{metrics.window_days} days, one column per acquisition month",
    )

    if metrics.by_month.empty:
        _empty_state("No users were acquired in this reference period.")
        return None

    return _column_chart(
        metrics,
        key="chart_customer_value",
        value_field="customer_value",
        value_title="Value per acquired user",
        axis_format="$,.0f",
        label_format="$,.2f",
        tooltip_title=f"{metrics.window_label} Customer Value",
    )


# ---------------------------------------------------------------------------
# Chart 2 -- purchase conversion rate by acquisition month
# ---------------------------------------------------------------------------

def render_conversion_chart(metrics: CohortMetrics) -> str | None:
    _heading(
        f"{metrics.window_label} Purchase Conversion Rate by Acquisition Month",
        "Share of each month's acquired users who ordered within their first "
        f"{metrics.window_days} days",
    )

    if metrics.by_month.empty:
        _empty_state("No users were acquired in this reference period.")
        return None

    return _column_chart(
        metrics,
        key="chart_conversion",
        value_field="conversion_rate",
        value_title="Share of acquired users",
        axis_format=".0%",
        label_format=".1%",
        tooltip_title=f"{metrics.window_label} Conversion Rate",
    )


def month_summary(metrics: CohortMetrics, month_label: str) -> pd.DataFrame:
    """Summary row for a selected acquisition month, at the charts' own grain."""
    frame = chart_frame(metrics)
    row = frame[frame.month_label == month_label]
    if row.empty:
        return pd.DataFrame()

    row = row.iloc[0]
    return pd.DataFrame(
        {
            "Acquisition Month": [month_label],
            "Acquired Users": [int(row.acquired_users)],
            "Purchasing Customers": [int(row.purchasing_customers)],
            f"{metrics.window_label} Purchase Conversion Rate": [
                float(row.conversion_rate)
            ],
            f"{metrics.window_label} Customer Value": [float(row.customer_value)],
        }
    )
