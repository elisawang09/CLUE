"""
styles.py
---------
Design tokens and global CSS.

A restrained, Tableau-like surface: light page, white cards, one accent hue.
The accent is categorical slot 1 from the validated palette and passes the
lightness, chroma and contrast checks against a white chart surface, which is
what the charts actually sit on.
"""

import streamlit as st

# --- color tokens ------------------------------------------------------------

SERIES = "#2a78d6"          # the one accent; both charts are single-series
SERIES_MUTED = "#a9c8ee"    # same hue, de-emphasised (never a second hue)
SERIES_DARK = "#1c5aa6"

# The one place a second and third hue are allowed. A period-over-period delta
# has a direction, and direction is the whole point of showing it -- an arrow
# in the accent blue would read as decoration rather than as up or down. Both
# are dark enough to clear WCAG AA on the card surface, and the arrow glyph
# carries the same information as the colour so it does not depend on it.
POSITIVE = "#1B7F4B"
NEGATIVE = "#B3261E"

PAGE_BG = "#F7F9FC"
SURFACE = "#FFFFFF"
BORDER = "#E3E8EF"
GRID = "#EEF1F6"

TEXT_PRIMARY = "#1B2A4E"
TEXT_SECONDARY = "#5B6472"
TEXT_MUTED = "#8A93A3"

FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", '
    "Arial, sans-serif"
)


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background: {PAGE_BG};
        }}
        [data-testid="stMainBlockContainer"] {{
            padding-top: 3rem;
            padding-bottom: 4rem;
            max-width: 1500px;
        }}

        /* Cards ------------------------------------------------------------ */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: {SURFACE};
            border-radius: 10px;
        }}

        /* Header ----------------------------------------------------------- */
        .bd-title {{
            font-family: {FONT};
            font-size: 3rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            letter-spacing: -0.025em;
            /* Room for ascenders: the glyphs were clipping against the
               container's top edge at the smaller size. */
            line-height: 1.25;
            padding-top: 0.1em;
            margin: 0;
        }}
        .bd-subtitle {{
            font-family: {FONT};
            font-size: 1rem;
            color: {TEXT_MUTED};
            margin: 0.15rem 0 0 0;
        }}

        /* KPI cards --------------------------------------------------------- */
        /* Titles run from one line ("Acquired Users") to three ("Orders per
           Purchasing Customer"). Reserving three keeps every value on the same
           baseline instead of floating at a different height per card. */
        .bd-kpi-label {{
            font-family: {FONT};
            font-size: 0.8rem;
            font-weight: 600;
            color: {SERIES};
            margin: 0 0 0.4rem 0;
            line-height: 1.3;
            min-height: 3.9em;
            /* Carries the metric description as a hover hint. The cursor and a
               dotted underline on hover are the only signals it is there, so
               they need to be present but not shouty. */
            cursor: help;
        }}
        .bd-kpi-label:hover {{
            text-decoration: underline dotted;
            text-underline-offset: 3px;
        }}
        /* The acquisition month the value describes. Sits above the value
           rather than below it, so the card reads "which cohort, then what it
           was worth" in one pass. */
        .bd-kpi-month {{
            font-family: {FONT};
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {TEXT_MUTED};
            margin: 0 0 0.15rem 0;
            min-height: 1.1em;
        }}
        .bd-kpi-value {{
            font-family: {FONT};
            font-size: 1.9rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            line-height: 1.1;
            letter-spacing: -0.02em;
        }}
        .bd-kpi-value.is-primary {{ font-size: 2.4rem; }}
        /* Reserved even when empty (a non-breaking space), so a card with a
           unit is no taller than one without. */
        .bd-kpi-unit {{
            font-family: {FONT};
            font-size: 0.8rem;
            color: {TEXT_SECONDARY};
            margin-top: 0.25rem;
            min-height: 1.2em;
        }}
        /* Change against the previous acquisition month. Reserved even when
           there is no previous month, so the first cohort in the data does not
           render a shorter card than every other. */
        .bd-kpi-delta {{
            font-family: {FONT};
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 0.3rem;
            min-height: 1.2em;
            line-height: 1.2;
        }}
        .bd-kpi-delta.is-up {{ color: {POSITIVE}; }}
        .bd-kpi-delta.is-down {{ color: {NEGATIVE}; }}
        .bd-kpi-delta.is-flat {{ color: {TEXT_MUTED}; }}
        .bd-kpi-delta .bd-delta-context {{
            color: {TEXT_MUTED};
            font-weight: 400;
        }}

        /* Section + chart headings ------------------------------------------ */
        .bd-chart-title {{
            font-family: {FONT};
            font-size: 1.05rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            margin: 0;
            min-height: 1.5em;
        }}
        /* One subtitle fits on a line and the other wraps to two. Reserving two
           keeps both plot areas starting at the same y, so the charts line up
           rather than sitting a row apart. */
        .bd-chart-subtitle {{
            font-family: {FONT};
            font-size: 0.85rem;
            color: {TEXT_MUTED};
            margin: 0.15rem 0 0.6rem 0;
            line-height: 1.4;
            min-height: 2.8em;
        }}

        /* Metric details panel ---------------------------------------------- */
        .bd-panel-label {{
            font-family: {FONT};
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: {TEXT_MUTED};
            margin: 1.1rem 0 0.3rem 0;
        }}
        .bd-panel-value {{
            font-family: {FONT};
            font-size: 2rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            line-height: 1.15;
        }}
        .bd-panel-text {{
            font-family: {FONT};
            font-size: 0.92rem;
            color: {TEXT_SECONDARY};
            line-height: 1.55;
        }}
        .bd-expression {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.9rem;
            background: {PAGE_BG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 0.7rem 0.9rem;
            color: {TEXT_PRIMARY};
        }}
        .bd-source {{
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.82rem;
            color: {TEXT_SECONDARY};
        }}
        .bd-breadcrumb {{
            font-family: {FONT};
            font-size: 0.78rem;
            color: {TEXT_MUTED};
            margin-bottom: 0.2rem;
        }}

        /* Buttons ----------------------------------------------------------- */
        div.stButton > button {{
            font-family: {FONT};
            border-radius: 7px;
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {SERIES};
            border-color: {SERIES};
            color: #FFFFFF;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {SERIES_DARK};
            border-color: {SERIES_DARK};
        }}
        /* Menu items read as links, not controls competing with the value */
        div.stButton > button[kind="tertiary"] {{
            padding: 0;
            color: {SERIES};
            font-size: 0.8rem;
            font-weight: 600;
        }}

        /* The ⋯ card menu trigger: quiet until you go looking for it.
           Streamlit gives this button full container width, an expand_more
           chevron beside our icon, and a negative right margin on the label
           row -- so the chevron sat outside the button's own rounded box.

           Selected on the testid rather than the card's st-key- class: key
           classes are only emitted for expanders, element containers and
           vertical blocks, not for a popover's trigger. Matching on the
           element name too (button[...]) outranks Streamlit's own emotion
           rules, which are injected later and would otherwise win the tie.
           These are the only popovers in the app, so a global rule is safe. */
        [data-testid="stPopover"] {{
            display: flex;
            justify-content: flex-end;
        }}
        button[data-testid="stPopoverButton"] {{
            width: auto;
            min-width: 0;
            min-height: 0;
            padding: 0.15rem 0.3rem;
            background: transparent;
            border: none;
            box-shadow: none;
            color: {TEXT_MUTED};
        }}
        /* Shrink-wrap the label row and drop its negative offset. */
        button[data-testid="stPopoverButton"] > div {{
            margin-right: 0;
            gap: 0;
        }}
        /* Drop the chevron -- ⋯ already reads as a menu, and the second glyph
           is what broke out of the box. */
        button[data-testid="stPopoverButton"] > div > div:last-child {{
            display: none;
        }}
        button[data-testid="stPopoverButton"]:hover {{
            background: {PAGE_BG};
            color: {SERIES};
        }}
        button[data-testid="stPopoverButton"]:focus:not(:active) {{
            border: none;
            box-shadow: none;
            color: {SERIES};
        }}
        /* Menu items sit flush and left-aligned inside the popover */
        [data-testid="stPopoverBody"] div.stButton > button {{
            text-align: left;
            justify-content: flex-start;
        }}
        [data-testid="stPopoverBody"] a {{
            font-size: 0.8rem;
            font-weight: 600;
        }}

        [data-testid="stElementToolbar"] {{ display: none; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def highlight_selected_card(metric_id: str | None) -> None:
    """Outline whichever KPI card is currently selected."""
    if not metric_id:
        return
    st.markdown(
        f"""
        <style>
        .st-key-kpi_{metric_id} [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > .st-key-kpi_{metric_id}) {{
            border: 1.5px solid {SERIES};
            box-shadow: 0 0 0 3px rgba(42, 120, 214, 0.12);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
