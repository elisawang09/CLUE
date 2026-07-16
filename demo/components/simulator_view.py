import streamlit as st
from .styles import get_detail_box_html
from .top_view import render_top_view
from .simulation_result_graph import render_simulation_graph
from utils.graph_styles import legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay
from utils.slider_calculations import (
    calculate_target_pltv,
    generate_initial_slider_values,
    recalculate_sliders_for_target,
    adjust_sliders_for_target,
)

# ---------------------------------------------------------------------------
# Goal Setting Controls
# ---------------------------------------------------------------------------

def _initialize_simulator_state() -> None:
    """Initialize session keys used by simulator controls and actions."""
    if "show_suggestions" not in st.session_state:
        st.session_state.show_suggestions = False
    if "checked_suggestions" not in st.session_state:
        st.session_state.checked_suggestions = {}
    if "simulation_started" not in st.session_state:
        st.session_state.simulation_started = False
    if "pltv" not in st.session_state:
        st.session_state.pltv = 10
    if "pltv_input" not in st.session_state:
        st.session_state.pltv_input = int(st.session_state.pltv)


def _render_step_slider() -> None:
    STEP_SIZE = 5

    """Render the compact PLTV step control with minus/input/plus actions."""
    def _decrement_pltv() -> None:
        """Decrease PLTV input by one step while enforcing lower bound."""
        st.session_state.pltv = max(10, int(st.session_state.pltv) - STEP_SIZE)
        st.session_state.pltv_input = int(st.session_state.pltv)

        # Recalculate slider values for new target
        recalculate_sliders_for_target()

    def _increment_pltv() -> None:
        """Increase PLTV input by one step while enforcing upper bound."""
        st.session_state.pltv = min(100, int(st.session_state.pltv) + STEP_SIZE)
        st.session_state.pltv_input = int(st.session_state.pltv)

        recalculate_sliders_for_target()

    def _sync_pltv_from_input() -> None:
        """Synchronize the step-control backing value from manual number input."""
        st.session_state.pltv = int(st.session_state.pltv_input)

        recalculate_sliders_for_target()

    # Hide native number_input steppers so only custom +/- buttons are visible.
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

    st.markdown("<h6 style='text-align: center;'>🎯 Aiming the metric to be (%)</h6>", unsafe_allow_html=True)

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
                step=STEP_SIZE,
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

        st.markdown("Current PLTV: " + f"**$100**", text_alignment="center", unsafe_allow_html=True)


def _render_goal_controls() -> None:
    """Render the left-card goal controls and recommendation trigger."""

    if "prob_active" not in st.session_state or "num_orders" not in st.session_state or "order_value" not in st.session_state:
        generate_initial_slider_values(st.session_state.pltv_input)

    with st.container(key="goal_controls_stack"):
        _render_step_slider()

        st.space(size='small')
        st.markdown("<h6 style='text-align: center;'>Probability of Active</h6>", unsafe_allow_html=True)
        st.slider(
            "Probability of Active",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.prob_active,
            label_visibility="collapsed",
            key="prob_active",
            on_change=lambda: adjust_sliders_for_target("prob")
        )
        st.space(size='small')

        st.markdown("<h6 style='text-align: center;'>Expected Number of Orders</h6>", unsafe_allow_html=True)
        st.slider(
            "Expected Number of Orders",
            min_value=0,
            max_value=10,
            value=st.session_state.num_orders,
            label_visibility="collapsed",
            key="num_orders",
            on_change=lambda: adjust_sliders_for_target("num_orders")
        )
        st.space(size='small')

        st.markdown("<h6 style='text-align: center;'>Expected Order Value ($)</h6>", unsafe_allow_html=True)
        st.slider(
            "Expected Order Value ($)",
            min_value=1,
            max_value=100,
            value=st.session_state.order_value,
            label_visibility="collapsed",
            key="order_value",
            on_change=lambda: adjust_sliders_for_target("order_value")
        )

        if st.button(
            "Recommend Strategies",
            key="get_suggestions",
            type="primary",
            width=200,
        ):
            st.session_state.show_suggestions = not st.session_state.show_suggestions
            st.rerun()


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

def _get_suggestion_texts() -> list[str]:
    """Return strategy suggestions shown in the simulator panel."""
    return [
        "Get 400 additional orders from existing customers",
        "Activate 200 new visitors and generate 2 orders from each of them at an average value of $60 ",
        "Encourage the top 30% of active customers to place 3 additional orders each",
    ]

def _render_suggested_fixes_panel() -> None:
    """Render suggestions and selection details in the right-top panel."""
    with st.container(border=True, height=285, key="card_sim_suggestions"):
        st.subheader("Suggested Strategies 🤖", help="AI generated suggestions to improve PLTV based on the current gap and data. Select one strategies to simulate its impact on the metric.")
        if not st.session_state.show_suggestions:
            return

        suggestions = _get_suggestion_texts()
        suggestion_details = """
        - +200 new active customers
        - +400 new orders added
        - Avg order value increased from $50 → $60 (for new data)
        - Total gross value increased by $24K
        """

        left_col, right_col = st.columns([0.6, 0.4], gap="small")

        with left_col:
            for idx, suggestion in enumerate(suggestions):
                checked = st.checkbox(suggestion, key=f"suggestion_{idx}")
                st.session_state.checked_suggestions[idx] = checked

            if st.button("Start Simulation", key="start_simulation", type="primary", width=150):
                st.session_state.simulation_started = True

        with right_col:
            for idx in range(len(suggestions)):
                if st.session_state.checked_suggestions.get(idx, False):
                    st.markdown(get_detail_box_html(suggestion_details), unsafe_allow_html=True)
                else:
                    st.empty()


def _render_simulation_output_panel() -> None:
    """Render simulation output summary for selected strategies."""
    with st.container(border=True, height=400, key="card_sim_output"):
        st.subheader("Simulation Results")
        if not st.session_state.simulation_started:
            st.write("Click Start Simulation to generate output here.")
            return

        selected_suggestions: list[str] = []
        if st.session_state.show_suggestions:
            suggestions = _get_suggestion_texts()
            selected_suggestions = [
                suggestion
                for idx, suggestion in enumerate(suggestions)
                if st.session_state.checked_suggestions.get(idx, False)
            ]

        if selected_suggestions:
            # ---------------------------------------------------------------------------
            # Legend
            # ---------------------------------------------------------------------------
            st.markdown(legend_style_html(), unsafe_allow_html=True)

            render_simulation_graph()

        else:
            st.write("No suggestions selected. Showing baseline simulation output.")


def render_simulator_view() -> None:
    """Render the simulator page with goal setup, suggestions, and output panels."""
    _initialize_simulator_state()
    inject_tooltip_overlay()

    render_top_view(button_text="Back to Main View", view_type="main")

    sim_col1, sim_col2 = st.columns([1.0, 3.5])

    with sim_col1:
        with st.container(border=True, height=700, key="card_sim_goal"):
            st.subheader("Set A Goal")
            _render_goal_controls()

    with sim_col2:
        _render_suggested_fixes_panel()
        _render_simulation_output_panel()