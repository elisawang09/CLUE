import streamlit as st
from .styles import get_detail_box_html
from .top_view import render_top_view

def render_simulator_view() -> None:
    # Initialize session state for suggestions
    if "show_suggestions" not in st.session_state:
        st.session_state.show_suggestions = False
    if "checked_suggestions" not in st.session_state:
        st.session_state.checked_suggestions = {}
    if "simulation_started" not in st.session_state:
        st.session_state.simulation_started = False

    render_top_view(button_text="Back to Main View", view_type="main")
    
    sim_col1, sim_col2 = st.columns([1.0, 3])
    with sim_col1:
        with st.container(border=True, height=640):
            st.subheader("Simulator Controls")
            st.slider("Active customer ratio", min_value=0.0, max_value=1.0, value=0.62)
            st.slider("Average orders per customer", min_value=0.0, max_value=20.0, value=4.5)
            st.slider("Average order value", min_value=0.0, max_value=500.0, value=44.0)

            if st.button("Get Suggestions", key="get_suggestions", use_container_width=True, type="primary"):
                st.session_state.show_suggestions = not st.session_state.show_suggestions
                st.rerun()

    with sim_col2:
        with st.container(border=True, height=310):
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
                        type="primary", width=200,):
                        st.session_state.simulation_started = True
                    
                # Right column: selected details
                with right_col:
                    for idx in range(len(suggestions)):
                        if st.session_state.checked_suggestions.get(idx, False):
                            st.markdown(get_detail_box_html(suggestion_details), unsafe_allow_html=True)
                        else:
                            st.empty()

        with st.container(border=True, height=310):
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