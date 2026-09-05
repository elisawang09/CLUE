import streamlit as st

# The metric CLUE explains. Participants arrive from the baseline dashboard
# with this metric already chosen, so there is no selector here -- every view
# checks against this name rather than a literal.
PRIMARY_METRIC = "90-Day Customer Value"


def render_top_view(button_text: str, view_type: str) -> None:
    """Render the common top bar with app title, metric name, and view switch button."""
    with st.container():
        col_title, col_metric, col_button = st.columns(
            [0.1, 0.3, 0.1],
            vertical_alignment="bottom",
        )

        with col_title:
            st.title("CLUE")

        with col_metric:
            st.markdown(
                f"<div style='padding-bottom:0.75rem; font-size:1.05rem; "
                f"color:#2C3770;'><b>{PRIMARY_METRIC}</b></div>",
                unsafe_allow_html=True,
            )

        with col_button:
            if st.button(
                button_text,
                key="view_switch_btn",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.active_view = view_type
                st.rerun()
