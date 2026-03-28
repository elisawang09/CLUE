import streamlit as st
from components.main_view import render_main_view
from components.simulator_view import render_simulator_view
from components.styles import inject_app_styles

st.set_page_config(layout="wide")

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

inject_app_styles()

if "active_view" not in st.session_state:
    st.session_state.active_view = "main"

if "search_query" not in st.session_state:
    st.session_state.search_query = None

if st.session_state.active_view == "simulator":
    render_simulator_view()
else:
    render_main_view()