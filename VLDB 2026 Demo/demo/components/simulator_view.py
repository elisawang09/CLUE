import streamlit as st
from .styles import get_detail_box_html
from .top_view import render_top_view

def render_step_slider() -> None:
    def _decrement_pltv() -> None:
        st.session_state.pltv = max(10, int(st.session_state.pltv) - 10)
        st.session_state.pltv_input = int(st.session_state.pltv)

    def _increment_pltv() -> None:
        st.session_state.pltv = min(100, int(st.session_state.pltv) + 10)
        st.session_state.pltv_input = int(st.session_state.pltv)

    def _sync_pltv_from_input() -> None:
        st.session_state.pltv = int(st.session_state.pltv_input)

    # Hide native number_input steppers to avoid showing a second +/- pair.
    st.markdown(
        """
        <style>
        [data-testid="stNumberInput"] button {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("###### 🎯 Aiming the metric to be (%)")
    with st.container(key="pltv_step_row"):
        col1, col2, col3 = st.columns([1, 0.5, 1], gap="small", vertical_alignment="center")
        with col1:
            _, col_minus = st.columns([0.5, 0.5], gap="small")
            with col_minus:
                st.button(
                    "➖︎",
                    key="div_minus",
                    use_container_width=True,
                    on_click=_decrement_pltv,
                    type="primary",
                )

        with col2:
            st.number_input(
                "🎯 Aiming the metric to be (%)",
                min_value=10,
                max_value=100,
                step=10,
                key="pltv_input",
                on_change=_sync_pltv_from_input,
                label_visibility="collapsed"
            )

        with col3:
            col_plus, _ = st.columns([0.5, 0.5], gap="small")
            with col_plus:
                st.button(
                    "➕︎",
                    key="pltv_plus",
                    use_container_width=True,
                    on_click=_increment_pltv,
                    type="primary",
                )
                
def render_simulator_view() -> None:
    # Initialize session state for suggestions
    if "show_suggestions" not in st.session_state:
        st.session_state.show_suggestions = False
    if "checked_suggestions" not in st.session_state:
        st.session_state.checked_suggestions = {}
    if "simulation_started" not in st.session_state:
        st.session_state.simulation_started = False
    if "pltv" not in st.session_state:
        st.session_state.pltv = 20
    if "pltv_input" not in st.session_state:
        st.session_state.pltv_input = int(st.session_state.pltv)

    render_top_view(button_text="Back to Main View", view_type="main")
    
    sim_col1, sim_col2 = st.columns([1.0, 3])
    with sim_col1:
        with st.container(border=True, height=640, key="card_sim_goal"):
            st.subheader("Set A Goal")
            # st.markdown(
            #     "<hr style='margin: 0.04rem 0 0.16rem 0; border: none; border-top: 1px solid rgba(49, 51, 63, 0.2);'>",
            #     unsafe_allow_html=True,
            # )
            with st.container(key="goal_controls_stack"):
                render_step_slider()

                st.markdown("###### Probability of Active")
                st.slider("Probability of Active", min_value=0.0, max_value=1.0, value=0.4, label_visibility="collapsed")
                st.markdown("###### Expected Number of Orders")
                st.slider("Expected Number of Orders", min_value=0, max_value=10, value=5, label_visibility="collapsed")
                st.markdown("###### Expected Order Value ($)")
                st.slider("Expected Order Value ($)", min_value=1, max_value=100, value=50, label_visibility="collapsed")

                if st.button(
                    "Recommend Strategies",
                    key="get_suggestions",
                    type="primary",
                    width=200,
                ):
                    st.session_state.show_suggestions = not st.session_state.show_suggestions
                    st.rerun()

    with sim_col2:
        with st.container(border=True, height=310, key="card_sim_suggestions"):
            st.subheader("Suggested Data Fixes")

            if st.session_state.show_suggestions:
                suggestions = [
                    "Get 400 additional orders from existing customers",
                    "Activate 200 new visitors and generate 2 orders from each of them at an average value of $60 ",
                    "Encourage the top 30% of active customers to place 3 additional orders each"
                ]
                
                suggestion_details = """- +200 new active customers
- +400 new orders added
- Avg order value increased from $50 → $60 (for new data)
- Total gross value increased by $24K"""
                
                left_col, right_col = st.columns([0.6, 0.4])
                
                # Left column: suggestions
                with left_col:
                    for idx, suggestion in enumerate(suggestions):
                        checked = st.checkbox(suggestion, key=f"suggestion_{idx}")
                        st.session_state.checked_suggestions[idx] = checked
                        
                    if st.button("Start Simulation", key="start_simulation",                        
                        # use_container_width=True, 
                        type="primary", width=150):
                        st.session_state.simulation_started = True
                    
                # Right column: selected details
                with right_col:
                    for idx in range(len(suggestions)):
                        if st.session_state.checked_suggestions.get(idx, False):
                            st.markdown(get_detail_box_html(suggestion_details), unsafe_allow_html=True)
                        else:
                            st.empty()

        with st.container(border=True, height=310, key="card_sim_output"):
            st.subheader("Simulation Output")
            if st.session_state.simulation_started:
                selected_suggestions = []
                if st.session_state.show_suggestions:
                    suggestions = [
                        "Get 400 additional orders from existing customers",
                        "Activate 200 new visitors and generate 2 orders from each of them at an average value of $60 ",
                        "Encourage the top 30% of active customers to place 3 additional orders each",
                    ]
                    selected_suggestions = [
                        suggestion
                        for idx, suggestion in enumerate(suggestions)
                        if st.session_state.checked_suggestions.get(idx, False)
                    ]

                st.write("Simulation started.")
                if selected_suggestions:
                    st.markdown("**Applied Suggestions**")
                    for suggestion in selected_suggestions:
                        st.markdown(f"- {suggestion}")
                else:
                    st.write("No suggestions selected. Showing baseline simulation output.")
            else:
                st.write("Click Start Simulation to generate output here.")