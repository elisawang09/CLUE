"""
Custom styling utilities for the simulator view.
"""

# Color definitions
CHECKBOX_COLOR = "#2C3770"
SUBHEADER_COLOR = "#2C3770"
TEXT_SELECTED_COLOR = "#E0EAFF"
TEXT_SELECTED_BG = "#2C377015"  # semi-transparent background
BORDER_COLOR = "#94B6FF"

# Pathway comparison cards. Hues are taken from the palette already in use --
# the panel accent for the live card, the provenance graph's ratio green and
# root amber for goal met / missed -- so the simulator reads as the same app as
# the provenance view rather than introducing a second colour language.
CARD_BORDER = "#DCE4F7"
CARD_HEADER_BG = "#EEF0FF"
CARD_MUTED_TEXT = "#7B7F87"
CARD_RULE = "#EDF0F7"
# Divides the two halves of a card -- a structural split, not the hairline
# between adjacent figures, so it carries more weight than CARD_RULE. At
# #EDF0F7 the line between the assumptions and what they imply was there in
# the markup and invisible on screen.
CARD_DIVIDER = "#C9D4EC"
GOAL_MET_TEXT = "#1A6640"
GOAL_MET_BG = "#E8F8EF"
GOAL_MISSED_TEXT = "#C97A10"
GOAL_MISSED_BG = "#FCE4C6"


def _bullets_to_html_list(content: str) -> str:
    """Convert markdown bullet lines into a HTML list for reliable rendering in custom containers."""
    items = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        items.append(line)

    if not items:
        return ""

    li_html = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul style=\"margin: 0; padding-left: 18px;\">{li_html}</ul>"


def _build_app_css() -> str:
    """Build all app-level CSS customizations as a single style block."""
    return f"""
    <style>
        :root {{
            --secondary-background-color: #FFFFFF;
        }}

        /* Global app background */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: #F4F7FD !important;
        }}

        [data-testid="stMainBlockContainer"] {{
            padding-top: 10px !important;
            padding-bottom: 80px !important;
        }}

        /* Keep bordered containers as white cards */
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {{
            background: #FFFFFF !important;
        }}

        [data-testid="stContainer"],
        [data-testid="stContainer"] > div {{
            background: #FFFFFF !important;
        }}

        /* Explicit white card styling via keyed containers */
        .st-key-card_sim_controls_row,
        .st-key-card_sim_comparison,
        .st-key-card_main_overview,
        .st-key-card_main_explanation,
        .st-key-card_main_provenance,
        .st-key-card_main_transformation,
        .st-key-card_sim_controls_row > div,
        .st-key-card_sim_comparison > div,
        .st-key-card_main_overview > div,
        .st-key-card_main_explanation > div,
        .st-key-card_main_provenance > div,
        .st-key-card_main_transformation > div {{
            background: #FFFFFF !important;
            border-color: #DDE6F4 !important;
            box-shadow: none !important;
        }}

        /* Remove default widget shadows for a flatter look */
        [data-testid="stSlider"] *,
        [data-baseweb="slider"] *,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div,
        [data-testid="stTextInput"] [data-baseweb="input"] > div {{
            box-shadow: none !important;
        }}

        /* Custom checkbox accent color */
        [data-testid="stCheckbox"] > label > div:first-child {{
            accent-color: {CHECKBOX_COLOR} !important;
        }}

        /* Global subheader color (st.subheader renders as h3) */
        [data-testid="stHeading"] h3 {{
            color: {SUBHEADER_COLOR} !important;
            font-size: 1.18rem !important;
            line-height: 1.25 !important;
        }}

        /* Slider track styling: thicker bar with custom colors */
        [data-testid="stSlider"] div[role="slider"] + div,
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div {{
            height: 10px !important;
            border-radius: 999px !important;
        }}

        /* Filled portion of slider track */
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div > div:first-child {{
            background: #2C3770 !important;
        }}

        /* Unfilled portion of slider track */
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div > div:last-child {{
            background: #C8D7F6 !important;
        }}

        /* Match control heights in the planning goal step row */
        .st-key-goal_step_row div.stButton > button {{
            min-height: 34px !important;
        }}

        .st-key-goal_step_row [data-testid="stNumberInput"] input {{
            height: 34px !important;
            text-align: center;
        }}

        .st-key-div_minus button,
        .st-key-goal_plus button {{
            color: transparent !important;
            position: relative;
        }}

        .st-key-div_minus button::before,
        .st-key-goal_plus button::before {{
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            color: #FFFFFF;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1;
        }}

        .st-key-div_minus button::before {{
            content: "−";
        }}

        .st-key-goal_plus button::before {{
            content: "+";
        }}

        /* Compact the controls row so five columns fit without scrolling */
        .st-key-card_sim_controls_row [data-testid="stSlider"],
        .st-key-card_sim_controls_row [data-testid="stNumberInput"],
        .st-key-card_sim_controls_row div.stButton {{
            width: 100% !important;
            margin-bottom: 0.04rem !important;
        }}

        .st-key-card_sim_controls_row [data-testid="stVerticalBlock"] > div {{
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}

        .st-key-card_sim_controls_row [data-testid="stMarkdownContainer"] p {{
            margin-bottom: 0.04rem !important;
            margin-top: 0.04rem !important;
        }}

        .st-key-card_main_explanation [data-testid="stMarkdownContainer"] p,
        .st-key-card_main_explanation [data-testid="stMarkdownContainer"] li {{
            /* Slightly smaller font for explanation text in AI-generated explanation card */
            font-size: 0.9rem !important;
            line-height: 1.45 !important;
        }}

        /* Make slider thumb larger than track and let it sit outside the bar */
        [data-testid="stSlider"] [data-baseweb="slider"],
        [data-testid="stSlider"] [data-baseweb="slider"] > div,
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div {{
            overflow: visible !important;
        }}

        [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
            width: 22px !important;
            height: 22px !important;
            border-radius: 50% !important;
            background: #2C3770 !important;
            border: 3px solid #FFFFFF !important;
            z-index: 2 !important;
        }}
    </style>
    """


def inject_checkbox_styles() -> None:
    """Inject app-wide CSS for cards, controls, typography, and interactive widgets."""
    import streamlit as st

    st.markdown(_build_app_css(), unsafe_allow_html=True)


def inject_app_styles():
    """Alias for app-wide style injection."""
    inject_checkbox_styles()

def get_selected_text_style() -> str:
    """Returns styled text wrapper for selected items in the comparison panel."""
    return f'<span style="color: {TEXT_SELECTED_COLOR}; background-color: {TEXT_SELECTED_BG}; padding: 2px 6px; border-radius: 3px;">'

def get_detail_box_html(content: str) -> str:
    """Returns HTML for the details box with styling."""
    list_html = _bullets_to_html_list(content)
    return f"""
    <div style="border: 2px solid {BORDER_COLOR};
                padding: 12px;
                border-radius: 5px;
                background-color: rgba(45, 55, 112, 0.03);
                font-size: 14px;
                line-height: 1.8;">
        {list_html}
    </div>
    """

def result_block_html(title: str, content: str) -> str:
    """
    One of the three result blocks: its heading and its bullets, together.

    Heading and box are emitted as a single element so the block can be
    stretched as a unit -- with the heading as a separate Streamlit element the
    box has nothing definite to fill, and the three boxes end at whatever
    height their own bullets happen to reach.

    Single line, no indentation: markdown reads a four-space indent as a code
    block.
    """
    return (
        f'<div class="clue-result-block">'
        f'<div class="clue-result-title">{title}</div>'
        f'<div class="clue-detail-box">{_bullets_to_html_list(content)}</div>'
        f"</div>"
    )


def scenario_rail_css() -> str:
    """
    The horizontal rail the pathway cards sit on, and the live scenario panel.

    Emitted flush-left. Leading whitespace means nothing to CSS but everything
    to markdown, which reads a four-space indent as a code block.

    Each card is a Streamlit container holding its HTML plus two buttons that
    CSS lifts on top of it: one covering the whole card, so clicking anywhere
    selects it, and a small one in the corner that removes it. HTML alone
    cannot carry a Streamlit click, and routing selection through the URL
    instead would reset the rail's scroll position on every click.

    Laying those containers out horizontally means flexing Streamlit's own
    vertical block, which is why this reaches for `data-testid`. The rest of
    the app already does the same.
    """
    return f"""
<style>
/* Scenario list on the left, results on the right. The left column keeps the
   width a card had on the old horizontal rail -- the rows got shorter, not
   narrower -- and everything else goes to the results, which carry the
   propagation graph and need the room. */
.st-key-sim_split [data-testid="stHorizontalBlock"] {{
flex-wrap: nowrap;
gap: 14px;
}}
.st-key-sim_split [data-testid="stColumn"]:first-child {{
flex: 0 0 250px;
min-width: 250px;
border-right: 1px solid {CARD_RULE};
padding-right: 14px;
}}
.st-key-sim_split [data-testid="stColumn"]:last-child {{
flex: 1 1 auto;
min-width: 0;
}}
/* Vertical, not horizontal: cards off the right edge of a rail go unseen. Six
   rows fit without scrolling; the cap is six, so the scroll is a safety net
   rather than the normal case. */
.st-key-scenario_list {{
overflow-y: auto;
overflow-x: hidden;
max-height: 430px;
/* Generous room on three sides: the bottom clears the last row's border,
   which otherwise sits exactly on the clip edge and loses its bottom line,
   and the sides leave space for a selected row's shadow -- overflow-x
   clips that too. */
padding: 2px 8px 16px 4px;
}}
.st-key-scenario_list::-webkit-scrollbar {{ width: 8px; }}
.st-key-scenario_list::-webkit-scrollbar-thumb {{
background: {CARD_BORDER};
border-radius: 4px;
}}
[class*="st-key-listrow_"] {{
position: relative;
}}
/* One scenario, compressed to what distinguishes it: the name, what it is
   worth, and the three assumptions that produced it. The implied pathway
   moved to the results panel, which is where you are looking once a row is
   selected. */
.clue-lite {{
border: 1px solid {CARD_BORDER};
border-radius: 8px;
background: #FFFFFF;
padding: 8px 10px;
margin-bottom: 8px;
}}
.clue-lite.is-selected {{
border: 2px solid {CHECKBOX_COLOR};
background: {CARD_HEADER_BG};
box-shadow: 0 2px 8px rgba(44, 55, 112, .16);
}}
.clue-lite-name {{
display: block;
font-weight: 700;
font-size: 12.5px;
color: {SUBHEADER_COLOR};
padding-right: 24px;
line-height: 1.3;
}}
.clue-lite-note {{
display: block;
font-weight: 400;
font-size: 10.5px;
color: {CARD_MUTED_TEXT};
padding-right: 24px;
line-height: 1.35;
}}
.clue-lite-mid {{
display: flex;
align-items: baseline;
justify-content: space-between;
gap: 8px;
margin-top: 4px;
}}
.clue-lite-val {{
font-variant-numeric: tabular-nums;
font-weight: 700;
font-size: 15px;
color: #2F3E7C;
}}
.clue-lite-sub {{
margin-top: 3px;
font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
font-size: 10.5px;
color: {CARD_MUTED_TEXT};
}}
/* The results panel's empty state: a scenario has to be chosen before there is
   anything to propagate. */
.clue-hint {{
display: flex;
align-items: center;
justify-content: center;
min-height: 320px;
padding: 24px;
text-align: center;
color: {CARD_MUTED_TEXT};
font-size: 13px;
line-height: 1.6;
}}
/* The whole-row select target: invisible, fills the slot, and sits under the
   remove button so the corner still removes rather than selects.

   Every wrapper between the element container and the button is stretched by
   depth-independent descendant rules. Naming the levels instead
   (`> div > div`) only worked for the nesting that happened to exist: the
   button kept its natural height, so just a bar across the top of the row was
   clickable while the rest of it was dead.

   !important throughout because the app sets --secondary-background-color to
   white at :root, and that feeds Streamlit's own button background. */
[class*="st-key-select_"] {{
position: absolute;
inset: 0;
z-index: 1;
}}
[class*="st-key-select_"],
[class*="st-key-select_"] div,
[class*="st-key-select_"] button {{
width: 100% !important;
height: 100% !important;
background: transparent !important;
border: none !important;
box-shadow: none !important;
}}
[class*="st-key-select_"] button,
[class*="st-key-select_"] button:active,
[class*="st-key-select_"] button:focus,
[class*="st-key-select_"] button:focus:not(:active) {{
padding: 0 !important;
margin: 0 !important;
border-radius: 8px !important;
color: transparent !important;
background: transparent !important;
box-shadow: none !important;
}}
[class*="st-key-select_"] button:hover {{
background: rgba(44, 55, 112, 0.06) !important;
}}
/* A small circle, dark enough to read on a white row and on the tinted
   background of a selected one. */
[class*="st-key-remove_"] {{
position: absolute;
top: 7px;
right: 7px;
width: auto !important;
z-index: 2;
background: transparent !important;
}}
[class*="st-key-remove_"] > div,
[class*="st-key-remove_"] > div > div {{
width: auto !important;
background: transparent !important;
}}
[class*="st-key-remove_"] button,
[class*="st-key-remove_"] button:active,
[class*="st-key-remove_"] button:focus,
[class*="st-key-remove_"] button:focus:not(:active) {{
height: 20px !important;
width: 20px !important;
min-height: 20px !important;
min-width: 20px !important;
padding: 0 !important;
margin: 0 !important;
border: none !important;
border-radius: 50% !important;
background: rgba(0, 0, 0, 0.3) !important;
color: #FFFFFF !important;
font-size: 11px !important;
line-height: 1 !important;
box-shadow: none !important;
}}
[class*="st-key-remove_"] button:hover {{
background: {GOAL_MISSED_TEXT} !important;
color: #FFFFFF !important;
}}
[class*="st-key-remove_"] button p {{
padding: 0 !important;
margin: 0 !important;
line-height: 1 !important;
font-size: 11px !important;
}}
.clue-card {{
width: 100%;
border: 1px solid {CARD_BORDER};
border-radius: 8px;
background: #FFFFFF;
font-size: 13px;
overflow: hidden;
}}
/* Selection has to be unmissable: the border alone read as noise once the
   cards sat side by side. The whole card lifts -- accent border, filled
   header, and a shadow. No label: the treatment says it without the words. */
.clue-card.is-selected {{
border: 2px solid {CHECKBOX_COLOR};
box-shadow: 0 2px 10px rgba(44, 55, 112, 0.18);
}}
.clue-card.is-selected .clue-card-title {{
background: {CHECKBOX_COLOR};
color: #FFFFFF;
}}
.clue-card.is-selected .clue-card-note {{
color: {TEXT_SELECTED_COLOR};
}}

.clue-card-title {{
background: {CARD_HEADER_BG};
color: {SUBHEADER_COLOR};
font-weight: 700;
padding: 6px 22px 6px 10px;
line-height: 1.3;
}}
.clue-card-note {{
display: block;
font-weight: 400;
font-size: 11px;
color: {CARD_MUTED_TEXT};
}}
.clue-card-section {{
padding: 8px 10px;
border-top: 1px solid {CARD_RULE};
}}
.clue-card-section:first-of-type {{ border-top: none; }}
.clue-card-label {{
font-size: 10.5px;
letter-spacing: 0.06em;
text-transform: uppercase;
color: {CARD_MUTED_TEXT};
margin-bottom: 3px;
}}
.clue-row {{
display: flex;
justify-content: space-between;
gap: 8px;
padding: 1px 0;
}}
.clue-row span:last-child {{
font-variant-numeric: tabular-nums;
font-weight: 600;
color: #2F3E7C;
}}
.clue-row.is-headline span:last-child {{ font-size: 14px; }}
.clue-goal {{
display: inline-block;
margin-top: 6px;
padding: 2px 8px;
border-radius: 10px;
font-size: 11px;
font-weight: 700;
}}
.clue-goal.met {{
background: {GOAL_MET_BG};
color: {GOAL_MET_TEXT};
}}
.clue-goal.missed {{
background: {GOAL_MISSED_BG};
color: {GOAL_MISSED_TEXT};
}}
/* The simulate button hugs its label; 40px each side keeps it from reading
   as a cramped chip without stretching it across the column. */
.st-key-start_simulation div.stButton {{
display: flex;
justify-content: flex-end;
}}
.st-key-start_simulation button p {{
padding-left: 40px;
padding-right: 40px;
}}
.clue-observed-range {{
text-align: center;
font-size: 11px;
color: {CARD_MUTED_TEXT};
margin-top: -6px;
}}
.clue-controls-heading {{
padding: 2px 4px 8px 4px;
}}
.clue-controls-heading b {{
color: {SUBHEADER_COLOR};
font-size: 15px;
}}
.clue-controls-heading span {{
color: {CARD_MUTED_TEXT};
font-size: 12.5px;
line-height: 1.5;
}}
/* The three result blocks.

   Their columns are nested inside the split, whose rules are written as
   descendant selectors and so match these too: the first block was picking up
   the scenario list's fixed 250px width and its right-hand rule, and the last
   was picking up flex-grow. Hence one narrow block, one wide one, and a stray
   vertical line. Reset all three to equal shares. */
.st-key-result_blocks [data-testid="stColumn"] {{
flex: 1 1 0 !important;
width: auto !important;
min-width: 0 !important;
border-right: none !important;
padding-right: 0 !important;
}}
/* Equal height as well as equal width: stretch the columns, then let each
   block fill its own. */
.st-key-result_blocks [data-testid="stHorizontalBlock"] {{
align-items: stretch !important;
}}
.st-key-result_blocks [data-testid="stColumn"] > div,
.st-key-result_blocks [data-testid="stColumn"] [data-testid="stVerticalBlock"],
.st-key-result_blocks [data-testid="stElementContainer"] {{
height: 100%;
}}
.clue-result-block {{
display: flex;
flex-direction: column;
gap: 6px;
height: 100%;
}}
.clue-result-title {{
font-weight: 700;
font-size: 14px;
color: {SUBHEADER_COLOR};
line-height: 1.4;
}}
.clue-detail-box {{
flex: 1 1 auto;
border: 2px solid {BORDER_COLOR};
padding: 12px;
border-radius: 5px;
background-color: rgba(45, 55, 112, 0.03);
font-size: 14px;
line-height: 1.8;
}}
/* A rule, not a second card: the band is what the sliders above it produce,
   so it belongs to the same block. Streamlit's own gap sits above the border,
   which is why the padding below it is the larger of the two. */
.st-key-scenario_strip {{
border-top: 1px solid {CARD_DIVIDER};
margin-top: 4px;
padding-top: 14px;
}}
/* The live scenario, laid out wide rather than tall.

   Its content is a headline plus four figures. As a narrow column beside the
   sliders that was six stacked lines and about 265px, which set the height of
   the whole control row and left the three sliders sitting in a quarter-screen
   of nothing. The same content as a band is one line of four stats. */
.clue-strip-value {{
font-size: 1.5rem;
font-weight: 700;
color: #2F3E7C;
font-variant-numeric: tabular-nums;
line-height: 1.2;
}}
.clue-strip-sub {{
color: #5A6270;
font-size: 12.5px;
line-height: 1.45;
}}
.clue-strip-stats {{
display: grid;
grid-template-columns: repeat(4, 1fr);
gap: 14px;
}}
.clue-strip-stat {{
border-left: 1px solid {CARD_RULE};
padding-left: 12px;
min-width: 0;
}}
.clue-strip-stat b {{
display: block;
font-size: 13.5px;
font-weight: 600;
color: #2F3E7C;
font-variant-numeric: tabular-nums;
white-space: nowrap;
}}
/* The four stats wrap as a block rather than one at a time, so the band never
   breaks into a ragged two-and-two. */
@media (max-width: 900px) {{
.clue-strip-stats {{ grid-template-columns: repeat(2, 1fr); }}
}}
.clue-strip-action {{
display: flex;
align-items: center;
justify-content: flex-end;
gap: 10px;
}}
</style>
"""


def scenario_row_html(
    title: str,
    note: str,
    headline: str,
    assumptions: str,
    goal_met: bool,
    goal_text: str,
    is_selected: bool,
) -> str:
    """
    One scenario, compressed to a row.

    Carries only what tells scenarios apart -- the name, what it is worth, and
    the three assumptions behind it. The implied pathway lives in the results
    panel beside it, which is where the reader is looking once a row is
    selected, and dropping it here is what lets six scenarios sit in view at
    once instead of two.

    Emitted as a single line with no indentation: markdown reads any line
    starting with four spaces as an indented code block, and the whole list is
    one st.markdown call.
    """
    note_html = f'<span class="clue-lite-note">{note}</span>' if note else ""
    state = "met" if goal_met else "missed"
    return (
        f'<div class="clue-lite{" is-selected" if is_selected else ""}">'
        f'<span class="clue-lite-name">{title}</span>'
        f"{note_html}"
        f'<div class="clue-lite-mid">'
        f'<span class="clue-lite-val">{headline}</span>'
        f'<span class="clue-goal {state}">{goal_text}</span>'
        f"</div>"
        f'<div class="clue-lite-sub">{assumptions}</div>'
        f"</div>"
    )


def scenario_strip_head_html(headline: str, sub: str) -> str:
    """The left end of the scenario band: what the assumptions are worth."""
    return (
        f'<div class="clue-card-label">Scenario</div>'
        f'<div class="clue-strip-value">{headline}</div>'
        f'<div class="clue-strip-sub">{sub}</div>'
    )


def scenario_strip_stats_html(stats: list[tuple[str, str]]) -> str:
    """
    The middle of the band: the implied data changes, side by side.

    Single line, no indentation -- markdown reads a four-space indent as a code
    block.
    """
    cells = "".join(
        f'<div class="clue-strip-stat">'
        f'<div class="clue-card-label">{label}</div><b>{value}</b>'
        f"</div>"
        for label, value in stats
    )
    return f'<div class="clue-strip-stats">{cells}</div>'


def scenario_hint_html(message: str) -> str:
    """The results panel before a scenario has been chosen."""
    return f'<div class="clue-hint">{message}</div>'


def get_checkbox_label_html(label: str, is_selected: bool = False) -> str:
    """Generate styled label text for checkbox."""
    if is_selected:
        style = f'style="color: {TEXT_SELECTED_COLOR}; background-color: {TEXT_SELECTED_BG}; padding: 2px 4px; border-radius: 2px;"'
        return f'<span {style}>{label}</span>'
    return label
