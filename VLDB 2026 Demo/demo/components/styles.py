"""
Custom styling utilities for the simulator view.
"""

# Color definitions
CHECKBOX_COLOR = "#2C3770"
SUBHEADER_COLOR = "#2C3770"
TEXT_SELECTED_COLOR = "#E0EAFF"
TEXT_SELECTED_BG = "#2C377015"  # semi-transparent background
BORDER_COLOR = "#94B6FF"


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
        .st-key-card_sim_goal,
        .st-key-card_sim_suggestions,
        .st-key-card_sim_output,
        .st-key-card_main_overview,
        .st-key-card_main_explanation,
        .st-key-card_main_provenance,
        .st-key-card_main_transformation,
        .st-key-card_sim_goal > div,
        .st-key-card_sim_suggestions > div,
        .st-key-card_sim_output > div,
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

        /* Match control heights in the PLTV step row */
        .st-key-pltv_step_row div.stButton > button {{
            min-height: 34px !important;
        }}

        .st-key-pltv_step_row [data-testid="stNumberInput"] input {{
            height: 34px !important;
            text-align: center;
        }}

        .st-key-div_minus button,
        .st-key-pltv_plus button {{
            color: transparent !important;
            position: relative;
        }}

        .st-key-div_minus button::before,
        .st-key-pltv_plus button::before {{
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

        .st-key-pltv_plus button::before {{
            content: "+";
        }}

        /* Compact and align controls in the simulator goal panel */
        .st-key-goal_controls_stack h6 {{
            margin: 0.03rem 0 0.01rem 0 !important;
        }}

        .st-key-goal_controls_stack [data-testid="stSlider"],
        .st-key-goal_controls_stack [data-testid="stNumberInput"],
        .st-key-goal_controls_stack div.stButton {{
            width: 100% !important;
            margin-bottom: 0.04rem !important;
        }}

        .st-key-goal_controls_stack [data-testid="stVerticalBlock"] > div {{
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}

        /* Pin final action near bottom of the goal card */
        .st-key-card_sim_goal {{
            position: relative;
        }}

        .st-key-goal_controls_stack {{
            padding-bottom: 2.9rem;
        }}

        .st-key-get_suggestions {{
            position: absolute;
            left: 50%;
            width: 200px;
            transform: translateX(-50%);
            bottom: 0.7rem;
            z-index: 3;
            margin: 0 !important;
        }}

        .st-key-get_suggestions > div.stButton,
        .st-key-get_suggestions > div.stButton > button {{
            width: 200px !important;
        }}

        .st-key-goal_controls_stack [data-testid="stMarkdownContainer"] p,
        .st-key-goal_controls_stack [data-testid="stMarkdownContainer"] h6 {{
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
    """Returns styled text wrapper for selected items in Simulator Suggestions."""
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

def get_checkbox_label_html(label: str, is_selected: bool = False) -> str:
    """Generate styled label text for checkbox."""
    if is_selected:
        style = f'style="color: {TEXT_SELECTED_COLOR}; background-color: {TEXT_SELECTED_BG}; padding: 2px 4px; border-radius: 2px;"'
        return f'<span {style}>{label}</span>'
    return label
