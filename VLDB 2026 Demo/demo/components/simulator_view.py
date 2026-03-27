import streamlit as st


def render_simulator_view() -> None:
    top_left, top_right = st.columns([0.2, 0.1])
    with top_left:
        st.title("Metric Simulator")
    with top_right:
        if st.button("Back to CLUE", key="back_to_main", use_container_width=True):
            st.session_state.active_view = "main"
            st.rerun()

    sim_col1, sim_col2 = st.columns([1.2, 2.8])
    with sim_col1:
        with st.container(border=True, height=300):
            st.subheader("Simulator Controls")
            st.slider("Active customer ratio", min_value=0.0, max_value=1.0, value=0.62)
            st.slider("Average orders per customer", min_value=0.0, max_value=20.0, value=4.5)
            st.slider("Average order value", min_value=0.0, max_value=500.0, value=44.0)

        with st.container(border=True, height=300):
            st.subheader("Scenario Notes")
            st.write("Use this view to run what-if simulations for selected metrics.")

    with sim_col2:
        with st.container(border=True, height=310):
            st.subheader("Suggested Data Fixes")
            st.write("This is your suggested data fixes.")

        with st.container(border=True, height=310):
            st.subheader("Simulation Output")
            st.write("This is your alternate full-page view for metric simulation results.")