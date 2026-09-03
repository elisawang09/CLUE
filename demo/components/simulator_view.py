import streamlit as st
from .styles import get_detail_box_html
from .top_view import PRIMARY_METRIC, render_top_view
from .simulation_result_graph import render_simulation_graph
from data.metrics import count, decimal, load_baseline, money, percent, whole_money
from data.scenario import Scenario, combine, goal_value, starters
from data.graph_data import simulation_deltas
from utils.graph_styles import legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay
from utils.slider_calculations import (
    CONVERSION_KEY,
    ORDERS_KEY,
    ORDER_VALUE_KEY,
    UPLIFT_INPUT_KEY,
    UPLIFT_KEY,
    UPLIFT_MAX,
    UPLIFT_MIN,
    UPLIFT_STEP,
    current_scenario,
    initialize_scenario_state,
    slider_bounds,
    uplift_percent,
)

# ---------------------------------------------------------------------------
# Goal Setting Controls
# ---------------------------------------------------------------------------

def _initialize_simulator_state(baseline) -> None:
    """Initialize session keys used by simulator controls and actions."""
    if "show_starters" not in st.session_state:
        st.session_state.show_starters = False
    if "simulation_started" not in st.session_state:
        st.session_state.simulation_started = False
    initialize_scenario_state(baseline)


GOAL_TITLE = (
    "🎯 Users acquired over the next 3 months should generate this much more "
    "value in their first 6 months (%)"
)

NUMBER_INPUT_CSS = """
    <style>
    [data-testid="stNumberInput"] button {
        display: none;
    }
    </style>
    """

# One heading height across the row, bottom-aligned: the titles then start and
# end level with one another, which is what puts the goal stepper on the same
# line as the three sliders however many lines a title wraps to.
CONTROLS_ROW_CSS = """
    <style>
    .st-key-card_sim_controls_row h6 {
        min-height: 3.6em;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        margin: 0 0 0.35rem 0 !important;
        line-height: 1.25;
    }
    </style>
    """


def _render_step_slider(
    baseline, title: str = GOAL_TITLE, inject_stepper_css: bool = True
) -> None:
    """
    Render the planning goal: how much more value than the reference group.

    `title` and `inject_stepper_css` exist for the row layout, which needs a
    shorter heading and injects the stepper CSS once for the whole row -- an
    injected style block inside a column pushes that column's content down.
    """

    def _decrement_uplift() -> None:
        st.session_state[UPLIFT_KEY] = max(
            UPLIFT_MIN, int(st.session_state[UPLIFT_KEY]) - UPLIFT_STEP
        )
        st.session_state[UPLIFT_INPUT_KEY] = int(st.session_state[UPLIFT_KEY])

    def _increment_uplift() -> None:
        st.session_state[UPLIFT_KEY] = min(
            UPLIFT_MAX, int(st.session_state[UPLIFT_KEY]) + UPLIFT_STEP
        )
        st.session_state[UPLIFT_INPUT_KEY] = int(st.session_state[UPLIFT_KEY])

    def _sync_uplift_from_input() -> None:
        st.session_state[UPLIFT_KEY] = int(st.session_state[UPLIFT_INPUT_KEY])

    # Hide native number_input steppers so only custom +/- buttons are visible.
    if inject_stepper_css:
        st.markdown(NUMBER_INPUT_CSS, unsafe_allow_html=True)

    st.markdown(
        f"<h6 style='text-align: center;'>{title}</h6>",
        unsafe_allow_html=True,
    )

    with st.container(key="goal_step_row"):
        col1, col2, col3 = st.columns([1, 0.5, 1], gap="small", vertical_alignment="center")
        with col1:
            _, col_minus = st.columns([0.5, 0.5], gap="small")
            with col_minus:
                st.button(
                    "➖︎",
                    key="div_minus",
                    use_container_width=True,
                    on_click=_decrement_uplift,
                    type="primary",
                )

        with col2:
            st.number_input(
                "Uplift over the historical baseline (%)",
                min_value=UPLIFT_MIN,
                max_value=UPLIFT_MAX,
                step=UPLIFT_STEP,
                key=UPLIFT_INPUT_KEY,
                on_change=_sync_uplift_from_input,
                label_visibility="collapsed",
            )

        with col3:
            col_plus, _ = st.columns([0.5, 0.5], gap="small")
            with col_plus:
                st.button(
                    "➕︎",
                    key="goal_plus",
                    use_container_width=True,
                    on_click=_increment_uplift,
                    type="primary",
                )

        goal = goal_value(baseline, uplift_percent())
        # Written as HTML rather than markdown: two money values on one line
        # would otherwise be read as LaTeX between the dollar signs.
        st.markdown(
            f"<div style='text-align:center;'>Historical Baseline: "
            f"<b>{money(baseline.customer_value)}</b> per acquired user"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;Goal: <b>{money(goal)}</b></div>",
            unsafe_allow_html=True,
        )


def _render_scenario_readout(baseline, scenario: Scenario) -> None:
    """State where the scenario lands relative to baseline and goal."""
    goal = goal_value(baseline, uplift_percent())
    change = (
        (scenario.customer_value / baseline.customer_value - 1) * 100
        if baseline.customer_value
        else 0.0
    )
    gap = scenario.customer_value - goal
    position = "above" if gap >= 0 else "below"

    st.markdown(
        f"<div style='text-align:center; font-size:0.9rem; line-height:1.5;'>"
        f"<b style='font-size:1.35rem;'>{money(scenario.customer_value)}</b><br>"
        f"<span style='color:#5A6270;'>{change:+.1f}% vs Historical Baseline<br>"
        f"{money(abs(gap))} {position} the goal</span></div>",
        unsafe_allow_html=True,
    )


def _render_controls_row(baseline) -> None:
    """
    The goal, the three assumptions, and the scenario readout, side by side.

    One row so every control is visible without scrolling.
    """
    bounds = slider_bounds(baseline)

    st.markdown(NUMBER_INPUT_CSS, unsafe_allow_html=True)
    st.markdown(CONTROLS_ROW_CSS, unsafe_allow_html=True)

    with st.container(border=True, height=250, key="card_sim_controls_row"):
        goal_col, conversion_col, orders_col, value_col, readout_col = st.columns(
            [1.15, 1, 1, 1, 1.1], gap="medium"
        )

        with goal_col:
            # Shorter heading so it wraps to the same height as the slider
            # titles, and the stepper CSS is injected once for the row above:
            # a style block inside a column offsets that column's content.
            _render_step_slider(
                baseline,
                title="🎯 Extra value from users acquired in the next 3 months (%)",
                inject_stepper_css=False,
            )

        with conversion_col:
            st.markdown(
                f"<h6 style='text-align: center;'>{baseline.window_label} Purchase "
                f"Conversion Rate</h6>",
                unsafe_allow_html=True,
            )
            minimum, maximum, step = bounds[CONVERSION_KEY]
            st.slider(
                "6-Month Purchase Conversion Rate",
                min_value=minimum,
                max_value=maximum,
                step=step,
                label_visibility="collapsed",
                key=CONVERSION_KEY,
                format="%.1f%%",
            )

        with orders_col:
            st.markdown(
                "<h6 style='text-align: center;'>Orders per Purchasing Customer</h6>",
                unsafe_allow_html=True,
            )
            minimum, maximum, step = bounds[ORDERS_KEY]
            st.slider(
                "Orders per Purchasing Customer",
                min_value=minimum,
                max_value=maximum,
                step=step,
                label_visibility="collapsed",
                key=ORDERS_KEY,
            )

        with value_col:
            st.markdown(
                "<h6 style='text-align: center;'>Average Order Value ($)</h6>",
                unsafe_allow_html=True,
            )
            minimum, maximum, step = bounds[ORDER_VALUE_KEY]
            st.slider(
                "Average Order Value ($)",
                min_value=minimum,
                max_value=maximum,
                step=step,
                label_visibility="collapsed",
                key=ORDER_VALUE_KEY,
                format="$%.2f",
            )

        with readout_col:
            st.markdown(
                "<h6 style='text-align: center;'>Scenario</h6>",
                unsafe_allow_html=True,
            )
            _render_scenario_readout(baseline, current_scenario(baseline))
            if st.button(
                "Generate Scenario Starters",
                key="get_starters",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.show_starters = not st.session_state.show_starters
                st.rerun()


# ---------------------------------------------------------------------------
# Scenario Starters
# ---------------------------------------------------------------------------

def _starter_detail(current: Scenario, starter) -> str:
    """
    High-level summary of one starter: its assumption and what follows from it.

    Read against the scenario currently in the controls, which is what the
    starter was built from.
    """
    scenario = starter.scenario
    return "\n".join(
        f"- {line}"
        for line in (
            starter.summary,
            f"Purchasing Customers: {count(current.purchasing_customers)} → "
            f"{count(scenario.purchasing_customers)}",
            f"Total Orders: {count(current.total_orders)} → {count(scenario.total_orders)}",
            f"Total Gross Order Value: {whole_money(current.total_gross_order_value)} → "
            f"{whole_money(scenario.total_gross_order_value)}",
            f"{PRIMARY_METRIC}: {money(current.customer_value)} → "
            f"{money(scenario.customer_value)}",
        )
    )


def selected_starters(baseline) -> list:
    """
    The starters currently ticked, in their fixed listed order.

    Rebuilt from the same current scenario the panel lists, so a tick always
    refers to the numbers on screen.
    """
    goal = goal_value(baseline, uplift_percent())
    return [
        starter
        for starter in starters(current_scenario(baseline), goal)
        if st.session_state.get(f"starter_{starter.key}", False)
    ]


def scenario_to_simulate(baseline) -> Scenario:
    """
    The scenario the results describe.

    Ticked starters take precedence -- each replaces the one factor it moves,
    on top of the controls; with none ticked, the controls are the scenario.
    """
    current = current_scenario(baseline)
    chosen = selected_starters(baseline)
    return combine(current, chosen) if chosen else current


def _render_scenario_starters_panel(baseline) -> None:
    """
    Render the Scenario Starters panel.

    Starters are hypothetical starting points for exploration, listed in a
    fixed order. None is marked best or recommended, and ticking one shows
    what it would imply rather than committing to it.
    """
    with st.container(border=True, height=285, key="card_sim_starters"):
        st.subheader(
            "Scenario Starters 🤖",
            help=(
                "Hypothetical starting points for exploration, not recommendations. "
                "Select one to see what it would imply, or set your own assumptions "
                "with the controls."
            ),
        )
        if not st.session_state.show_starters:
            st.write(
                "Click Generate Scenario Starters for a few hypothetical starting "
                "points, or set your own assumptions with the controls."
            )
            return

        current = current_scenario(baseline)
        goal = goal_value(baseline, uplift_percent())
        listed = starters(current, goal)

        left_col, right_col = st.columns([0.6, 0.4], gap="small")

        with left_col:
            for starter in listed:
                st.checkbox(
                    f"{starter.name} — {starter.summary}",
                    key=f"starter_{starter.key}",
                )

            if st.button("Start Simulation", key="start_simulation", type="primary", width=150):
                st.session_state.simulation_started = True

        with right_col:
            for starter in listed:
                if st.session_state.get(f"starter_{starter.key}", False):
                    st.markdown(
                        get_detail_box_html(_starter_detail(current, starter)),
                        unsafe_allow_html=True,
                    )
                else:
                    st.empty()


# ---------------------------------------------------------------------------
# Simulation results
# ---------------------------------------------------------------------------

def _assumption_lines(baseline, scenario: Scenario) -> list[str]:
    """Only the factors a participant actually moved away from the baseline."""
    rows = [
        (
            f"{baseline.window_label} Purchase Conversion Rate",
            percent(baseline.conversion_rate),
            percent(scenario.conversion_rate),
            baseline.conversion_rate,
            scenario.conversion_rate,
        ),
        (
            "Orders per Purchasing Customer",
            decimal(baseline.orders_per_purchasing_customer),
            decimal(scenario.orders_per_purchasing_customer),
            baseline.orders_per_purchasing_customer,
            scenario.orders_per_purchasing_customer,
        ),
        (
            "Average Order Value",
            money(baseline.average_order_value),
            money(scenario.average_order_value),
            baseline.average_order_value,
            scenario.average_order_value,
        ),
    ]
    changed = [
        f"{label}: {before} → {after}"
        for label, before, after, base_value, scenario_value in rows
        if abs(scenario_value - base_value) > 1e-9
    ]
    return changed or ["Every factor held at its historical baseline value."]


def _consequence_lines(baseline, scenario: Scenario) -> list[str]:
    return [
        f"Purchasing Customers: {count(baseline.purchasing_customers)} → "
        f"{count(scenario.purchasing_customers)}",
        f"Total Orders: {count(baseline.total_orders)} → {count(scenario.total_orders)}",
        f"Total Gross Order Value: {whole_money(baseline.total_gross_order_value)} → "
        f"{whole_money(scenario.total_gross_order_value)}",
    ]


def _result_lines(baseline, scenario: Scenario) -> list[str]:
    goal = goal_value(baseline, uplift_percent())
    change = (
        (scenario.customer_value / baseline.customer_value - 1) * 100
        if baseline.customer_value
        else 0.0
    )
    position = "above" if scenario.customer_value >= goal else "below"
    return [
        f"{PRIMARY_METRIC}: {money(baseline.customer_value)} → "
        f"{money(scenario.customer_value)}  ({change:+.1f}%)",
        f"Goal: {money(goal)} — the scenario result is {position} it.",
    ]


def _render_simulation_output_panel(baseline) -> None:
    """Render the scenario's assumptions, consequences, result, and propagation."""
    with st.container(border=True, height=400, key="card_sim_output"):
        st.subheader("Simulation Results")
        if not st.session_state.simulation_started:
            st.write("Click Start Simulation to generate output here.")
            return

        scenario = scenario_to_simulate(baseline)
        chosen = selected_starters(baseline)
        st.caption(
            "From the selected Scenario Starters: "
            + ", ".join(starter.name for starter in chosen)
            if chosen
            else "From the assumptions set in the controls."
        )

        blocks = (
            ("Scenario assumptions", _assumption_lines(baseline, scenario)),
            ("Computed consequences", _consequence_lines(baseline, scenario)),
            ("Scenario result", _result_lines(baseline, scenario)),
        )
        columns = st.columns(len(blocks), gap="small")
        for column, (title, lines) in zip(columns, blocks):
            with column:
                st.markdown(f"###### {title}")
                st.markdown(
                    get_detail_box_html("\n".join(f"- {line}" for line in lines)),
                    unsafe_allow_html=True,
                )

        # ---------------------------------------------------------------------------
        # Legend
        # ---------------------------------------------------------------------------
        st.markdown(legend_style_html(), unsafe_allow_html=True)

        render_simulation_graph(deltas=simulation_deltas(baseline, scenario))


def render_simulator_view() -> None:
    """
    Render the simulator page.

    Controls across the first row, then Scenario Starters and the results
    below, both full width.
    """
    baseline = load_baseline()

    _initialize_simulator_state(baseline)
    inject_tooltip_overlay()

    render_top_view(button_text="Back to Main View", view_type="main")

    _render_controls_row(baseline)
    _render_scenario_starters_panel(baseline)
    _render_simulation_output_panel(baseline)
