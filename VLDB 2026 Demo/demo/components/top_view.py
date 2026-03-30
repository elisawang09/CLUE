import streamlit as st

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
            metric_suggestions = [
                "Page Views",
                "Paying Users",
                "Retention Rate",
                "Total Revenue",
                "Profit",
                "Purchase Frequency",
                "Product Sales",
                "PLTV",
            ]

            st.selectbox(
                "",
                options=metric_suggestions,
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
