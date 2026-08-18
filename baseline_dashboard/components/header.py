"""Dashboard title block."""

import streamlit as st


def render_header() -> None:
    st.markdown(
        """
        <div>
          <p class="bd-title">Customer Value Dashboard</p>
          <p class="bd-subtitle">E-commerce Growth Overview</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
