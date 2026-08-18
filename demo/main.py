import streamlit as st
from components.main_view import render_main_view
from components.simulator_view import render_simulator_view
from components.styles import inject_app_styles
from components.top_view import METRIC_SUGGESTIONS

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

def _preselected_metric() -> str | None:
    """
    Metric named by a ?metric= link, if it is one we actually offer.

    The baseline dashboard links here with a metric preselected. Unrecognized
    values are ignored rather than raising: Streamlit rejects a selectbox
    session_state value that is not among its options, and a bad link should
    never break the app in front of a participant.
    """
    requested = st.query_params.get("metric")
    return requested if requested in METRIC_SUGGESTIONS else None


def _initialize_session_state() -> None:
    """Initialize global session keys used by navigation and search."""
    if "active_view" not in st.session_state:
        st.session_state.active_view = "main"
    if "search_query" not in st.session_state:
        st.session_state.search_query = _preselected_metric()

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