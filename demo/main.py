import streamlit as st
from components.main_view import render_main_view
from components.simulator_view import render_simulator_view
from components.styles import inject_app_styles
# The baseline dashboard links in with ?metric=, ?start= and ?end=. CLUE
# explains one metric and names it in the top bar, so ?metric= is accepted and
# ignored -- the handoff works whatever it says, and no link can land a
# participant on an empty page. The period is read in data/metrics.py, which
# falls back to the dashboard's own default when it is absent or malformed.

def _inject_primary_button_style() -> None:
    """Apply consistent styling for primary buttons across the app."""
    st.markdown(
        """
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #2C3770;
            color: #ffffff;
            border: 1px solid #2C3770;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #2C3770;
            color: #ffffff;
            border: 1px solid #2C3770;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _initialize_session_state() -> None:
    """Initialize global session keys used by navigation."""
    if "active_view" not in st.session_state:
        st.session_state.active_view = "main"

def _render_active_view() -> None:
    """Render the current page based on active_view."""
    if st.session_state.active_view == "simulator":
        render_simulator_view()
    else:
        render_main_view()

def main() -> None:
    """Configure the Streamlit app and render the selected view."""
    st.set_page_config(layout="wide")
    _inject_primary_button_style()
    inject_app_styles()
    _initialize_session_state()
    _render_active_view()

main()