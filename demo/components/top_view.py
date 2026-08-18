import streamlit as st

# Metrics offered in the search box. Module-level so main.py can validate an
# incoming ?metric= parameter against it -- Streamlit raises if a selectbox's
# session_state value is not one of its options.
METRIC_SUGGESTIONS = [
    "Page Views",
    "Paying Users",
    "PLTV",
    "Retention Rate",
    "Total Revenue",
    "Profit",
]


def render_top_view(button_text: str, view_type: str) -> None:
    """Render the common top bar with app title, metric selector, and view switch button."""
    with st.container():
        col_title, col_search, col_button = st.columns(
            [0.1, 0.3, 0.1],
            vertical_alignment="bottom",
        )

        with col_title:
            st.title("CLUE")

        with col_search:
            st.selectbox(
                "",
                options=METRIC_SUGGESTIONS,
                index=None,
                key="search_query",
                placeholder="Search a metric (e.g., total revenue)",
            )

        with col_button:
            if st.button(
                button_text,
                key="search_btn",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.active_view = view_type
                st.rerun()
