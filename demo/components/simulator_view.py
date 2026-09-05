import streamlit as st
from .styles import (
    result_block_html,
    scenario_hint_html,
    scenario_rail_css,
    scenario_row_html,
    scenario_strip_head_html,
    scenario_strip_stats_html,
)
from .top_view import PRIMARY_METRIC, render_top_view
from .simulation_result_graph import render_simulation_graph
from data.metrics import (
    count,
    decimal,
    load_baseline,
    md,
    money,
    percent,
    whole_money,
)
from data.scenario import (
    Scenario,
    from_baseline,
    from_observed_best,
    goal_value,
)
from data.graph_data import simulation_deltas
from utils.graph_styles import legend_style_html
from utils.tooltip_overlay import inject_tooltip_overlay
from utils.slider_calculations import (
    CURRENT_CARD_ID,
    MAX_RAIL_CARDS,
    CONVERSION_KEY,
    ORDERS_KEY,
    ORDER_VALUE_KEY,
    UPLIFT_INPUT_KEY,
    UPLIFT_KEY,
    UPLIFT_MAX,
    UPLIFT_MIN,
    UPLIFT_STEP,
    can_pin,
    current_scenario,
    initialize_scenario_state,
    next_scenario_name,
    pin_scenario,
    pinned_scenarios,
    remove_pinned,
    select_card,
    selected_card_id,
    slider_bounds,
    uplift_percent,
)

# ---------------------------------------------------------------------------
# Goal Setting Controls
# ---------------------------------------------------------------------------

def _initialize_simulator_state(baseline) -> None:
    """Initialize session keys used by simulator controls and actions."""
    initialize_scenario_state(baseline)


GOAL_TITLE = (
    "🎯 Users acquired over the next 3 months should generate this much more "
    "value in their first 90 days (%)"
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


def _render_scenario_strip(baseline) -> None:
    """
    The live scenario, as a band under the assumptions rather than a column
    beside them.

    Its content is a headline plus four figures. Stacked in a narrow column it
    ran about 265px, which set the height of the whole control row and left the
    three sliders — 110px of content each — sitting in a quarter-screen of
    nothing. Laid out wide it is a third of that, and the row reads as inputs
    then outcome rather than interleaving the two.

    The assumptions are the sliders directly above, so they are not repeated
    here; that is what still separates this from a pinned row.

    Rendered inside the assumptions card rather than as a card of its own: the
    band is what those sliders produce, so a rule between them reads as one
    block with two halves, where two cards read as two unrelated things.
    """
    scenario = current_scenario(baseline)
    goal = goal_value(baseline, uplift_percent())
    change = (
        (scenario.customer_value / baseline.customer_value - 1) * 100
        if baseline.customer_value
        else 0.0
    )
    gap = scenario.customer_value - goal
    met = gap >= 0

    with st.container(key="scenario_strip"):
        head_col, stats_col, action_col = st.columns(
            [1.15, 3.1, 1.25], gap="medium", vertical_alignment="center"
        )

        with head_col:
            st.markdown(
                scenario_strip_head_html(
                    headline=money(scenario.customer_value),
                    sub=(
                        f"{change:+.1f}% vs baseline &nbsp;·&nbsp; "
                        f"{money(abs(gap))} {'above' if met else 'below'} goal"
                    ),
                ),
                unsafe_allow_html=True,
            )

        with stats_col:
            st.markdown(
                scenario_strip_stats_html(_pathway_rows(baseline, scenario)),
                unsafe_allow_html=True,
            )

        with action_col:
            st.markdown(
                f'<div class="clue-strip-action">'
                f'<span class="clue-goal {"met" if met else "missed"}">'
                f'{"✓ meets goal" if met else "below goal"}</span></div>',
                unsafe_allow_html=True,
            )
            # Slots taken by cards that are not pinned scenarios -- today just
            # "Best observed". Passing the whole list length instead counted
            # every pinned scenario twice.
            other_cards = len(comparison_cards(baseline)) - len(pinned_scenarios())
            room = can_pin(other_cards)
            st.button(
                f"📌 Pin as Scenario {next_scenario_name()}" if room
                else f"📌 List is full ({MAX_RAIL_CARDS} scenarios)",
                key="pin_scenario",
                type="primary",
                use_container_width=True,
                disabled=not room,
                help=None if room else "Remove a scenario to pin another.",
                on_click=pin_scenario,
                args=(current_scenario(baseline), other_cards),
            )


def _observed_caption(low: str, high: str, baseline) -> str:
    """
    What this factor actually did across the reference period.

    Context, never a limit: the sliders stay open to values the history has
    never seen, because "what if a campaign pushed this past anything we have
    done" is exactly the kind of question the simulator exists for. Knowing
    where that boundary sits is what makes the answer readable.
    """
    return (
        f"<div class='clue-observed-range'>{baseline.period_label} range: "
        f"{low} – {high}</div>"
    )


def _render_controls_row(baseline) -> None:
    """
    The goal, the three assumptions, and the scenario readout, side by side.

    One row so every control is visible without scrolling.
    """
    bounds = slider_bounds(baseline)

    st.markdown(NUMBER_INPUT_CSS, unsafe_allow_html=True)
    st.markdown(CONTROLS_ROW_CSS, unsafe_allow_html=True)

    st.markdown(
        f"<div class='clue-controls-heading'>"
        f"<b>Metric profile assumptions for the next acquisition cohort</b><br>"
        f"<span>Assume users acquired in {baseline.future_period_label} look "
        f"roughly like this over their first {baseline.window_days} days. "
        f"Below, that profile is translated into a concrete pathway you can pin "
        f"and compare.</span></div>",
        unsafe_allow_html=True,
    )

    # No fixed height, and no scenario column: the readout is a band beneath
    # the inputs inside this same card, so every column in the row above it is
    # an input and they are all about the same height.
    with st.container(border=True, key="card_sim_controls_row"):
        goal_col, conversion_col, orders_col, value_col = st.columns(
            [1.35, 1, 1, 1], gap="medium"
        )

        with goal_col:
            # Shorter heading so it wraps to the same height as the slider
            # titles, and the stepper CSS is injected once for the row above:
            # a style block inside a column offsets that column's content.
            _render_step_slider(
                baseline,
                title=(
                    f"🎯 Extra {baseline.window_days}-day value from users "
                    f"acquired in the next 3 months (%)"
                ),
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
                f"{baseline.window_label} Purchase Conversion Rate",
                min_value=minimum,
                max_value=maximum,
                step=step,
                label_visibility="collapsed",
                key=CONVERSION_KEY,
                format="%.1f%%",
            )
            low, high = baseline.observed_range("conversion_rate")
            st.markdown(
                _observed_caption(percent(low), percent(high), baseline),
                unsafe_allow_html=True,
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
            low, high = baseline.observed_range("orders_per_purchasing_customer")
            st.markdown(
                _observed_caption(decimal(low), decimal(high), baseline),
                unsafe_allow_html=True,
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
            low, high = baseline.observed_range("average_order_value")
            st.markdown(
                _observed_caption(money(low), money(high), baseline),
                unsafe_allow_html=True,
            )

        _render_scenario_strip(baseline)


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------

def _pathway_rows(baseline, scenario: Scenario) -> list[tuple[str, str]]:
    """
    What one set of assumptions implies, against the same future cohort.

    Both sides use the future acquisition volume, so "before" is what the next
    three months would look like if nothing changed -- not the smaller cohort
    CLUE is explaining, which would make the arrow a comparison between two
    different-sized groups.
    """
    before = from_baseline(baseline)
    return [
        ("Future users", count(scenario.acquired_users)),
        (
            "Purchasing",
            f"{count(before.purchasing_customers)} → "
            f"{count(scenario.purchasing_customers)}",
        ),
        (
            "Orders",
            f"{count(before.total_orders)} → {count(scenario.total_orders)}",
        ),
        (
            "Gross value",
            f"{whole_money(before.total_gross_order_value)} → "
            f"{whole_money(scenario.total_gross_order_value)}",
        ),
    ]


def _assumption_rows(baseline, scenario: Scenario) -> list[tuple[str, str]]:
    return [
        (f"{baseline.window_label} Conversion", percent(scenario.conversion_rate)),
        ("Orders / Customer", decimal(scenario.orders_per_purchasing_customer)),
        ("Avg Order Value", money(scenario.average_order_value)),
    ]


def _headline_row(baseline, scenario: Scenario) -> tuple[str, str]:
    before = from_baseline(baseline)
    return (
        "Customer Value",
        f"{money(before.customer_value)} → {money(scenario.customer_value)}",
    )


def comparison_cards(baseline) -> list[tuple[str, str, str, Scenario]]:
    """
    Every card on the rail: (id, title, note, scenario).

    The live scenario is *not* here -- it lives in the control row, beside the
    sliders that produce it, so a participant sees it change as they drag. A
    copy of it on the rail was showing the same thing twice.

    The observed-best card is a starting point for someone facing three sliders
    with no obvious place to begin; it is removable like any pinned card.
    """
    cards: list[tuple[str, str, str, Scenario]] = []
    if st.session_state.get("show_reference_card", True):
        cards.append(
            (
                REFERENCE_CARD_ID,
                "Best observed",
                f"each factor at its best month in {baseline.period_label} — "
                f"a composite, not one actual month",
                from_observed_best(baseline),
            )
        )
    cards += [
        (name, f"Scenario {name}", "pinned", scenario)
        for name, scenario in pinned_scenarios()
    ]
    return cards


REFERENCE_CARD_ID = "__reference__"


def scenario_to_simulate(baseline) -> Scenario:
    """
    The scenario the results describe.

    A selected card if there is one, otherwise the live scenario -- so trying
    a set of assumptions never requires pinning it first.
    """
    selected = selected_card_id()
    for card_id, _, _, scenario in comparison_cards(baseline):
        if card_id == selected:
            return scenario
    return current_scenario(baseline)


def selected_card_title(baseline) -> str:
    selected = selected_card_id()
    for card_id, title, _, _ in comparison_cards(baseline):
        if card_id == selected:
            return title
    return "the current settings"


def _toggle_card(card_id: str) -> None:
    """
    Select a card, or return to the live scenario if it was already selected.

    A callback, not a post-render branch: Streamlit runs `on_click` before the
    script body, so the rail is drawn from state that already reflects the
    click. Mutating afterwards and calling `st.rerun()` leaves the removed
    card's keyed container behind as a ghost.
    """
    select_card(CURRENT_CARD_ID if selected_card_id() == card_id else card_id)


def _remove_card(card_id: str) -> None:
    """Drop a card from the rail, falling back to the live scenario."""
    if card_id == REFERENCE_CARD_ID:
        st.session_state.show_reference_card = False
    else:
        remove_pinned(card_id)
    if selected_card_id() == card_id:
        select_card(CURRENT_CARD_ID)


def _render_comparison_and_results(baseline) -> None:
    """
    Scenario list on the left, simulation results on the right.

    One row rather than two stacked ones. Choosing a scenario and reading what
    it implies is a single glance sideways, not a scroll past the fold -- which
    also means the Simulate button, the started/not-started state, and the
    scroll-into-view script all stop being needed. Clicking a row is the whole
    interaction.
    """
    goal = goal_value(baseline, uplift_percent())
    cards = comparison_cards(baseline)
    selected = selected_card_id()
    chosen = next(
        (card for card in cards if card[0] == selected), None
    )

    with st.container(border=True, key="card_sim_comparison"):
        with st.container(key="sim_split"):
            list_col, results_col = st.columns([1, 3], gap="medium")

            with list_col:
                st.markdown("###### Scenarios")
                st.caption(
                    f"{count(baseline.future_acquired_users)} users acquired "
                    f"{baseline.future_period_label} · goal {md(money(goal))}"
                )
                if not cards:
                    st.caption(
                        "Nothing pinned yet — set assumptions above and pin them "
                        "to compare here."
                    )
                else:
                    _render_scenario_list(baseline, cards, goal, selected)

            with results_col:
                _render_results_column(baseline, chosen)


def _render_scenario_list(baseline, cards, goal: float, selected: str) -> None:
    """The left column: one compact row per scenario, click to select."""
    with st.container(key="scenario_list"):
        for card_id, title, note, scenario in cards:
            with st.container(key=f"listrow_{card_id}"):
                met = scenario.customer_value >= goal
                st.markdown(
                    scenario_row_html(
                        title=title,
                        note=note,
                        headline=money(scenario.customer_value),
                        assumptions=(
                            f"{percent(scenario.conversion_rate)} · "
                            f"{decimal(scenario.orders_per_purchasing_customer)} · "
                            f"{money(scenario.average_order_value)}"
                        ),
                        goal_met=met,
                        goal_text="✓ meets goal" if met else "below goal",
                        is_selected=card_id == selected,
                    ),
                    unsafe_allow_html=True,
                )
                # Both buttons are lifted on top of the row by CSS: clicking
                # anywhere selects, the corner removes. Clicking the selected
                # row again clears the selection and returns the results panel
                # to its hint.
                st.button(
                    "Select",
                    key=f"select_{card_id}",
                    use_container_width=True,
                    on_click=_toggle_card,
                    args=(card_id,),
                )
                st.button(
                    "✕",
                    key=f"remove_{card_id}",
                    help=f"Remove {title}",
                    on_click=_remove_card,
                    args=(card_id,),
                )


def _render_results_column(baseline, chosen) -> None:
    """
    The right column: what the selected scenario implies, and its propagation.

    With nothing selected there is nothing to propagate, so the panel says so
    rather than showing a graph of the scenario the sliders happen to describe
    -- those numbers are already on screen in the control row above.
    """
    if chosen is None:
        st.markdown("###### Simulation Results")
        st.markdown(
            scenario_hint_html(
                "Select a scenario on the left to see what it implies "
                "and how the change propagates through the metric."
            ),
            unsafe_allow_html=True,
        )
        return

    _, title, _, scenario = chosen
    st.markdown(f"###### Simulation Results — {title}")

    blocks = (
        ("Scenario assumptions", _assumption_lines(baseline, scenario)),
        ("Implied Data Changes", _consequence_lines(baseline, scenario)),
        ("Scenario result", _result_lines(baseline, scenario)),
    )
    # Keyed so the split's column rules, which are descendant selectors, can be
    # reset for these nested columns -- otherwise the first block inherits the
    # scenario list's fixed width and the last one inherits flex-grow.
    with st.container(key="result_blocks"):
        columns = st.columns(len(blocks), gap="small")
        for column, (block_title, lines) in zip(columns, blocks):
            with column:
                st.markdown(
                    result_block_html(
                        block_title, "\n".join(f"- {line}" for line in lines)
                    ),
                    unsafe_allow_html=True,
                )

    st.markdown(legend_style_html(), unsafe_allow_html=True)
    render_simulation_graph(deltas=simulation_deltas(baseline, scenario))


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
    """
    Absolute counts, both sides on the future acquisition volume.

    Comparing against the explained cohort's own counts would put a group of
    31 users beside a group of 448 and call the difference a consequence of the
    assumptions.
    """
    before = from_baseline(baseline)
    return [
        f"Future Acquired Users ({baseline.future_period_label}): "
        f"{count(scenario.acquired_users)}",
        f"Purchasing Customers: {count(before.purchasing_customers)} → "
        f"{count(scenario.purchasing_customers)}",
        f"Total Orders: {count(before.total_orders)} → "
        f"{count(scenario.total_orders)}",
        f"Total Gross Order Value: {whole_money(before.total_gross_order_value)} → "
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


def render_simulator_view() -> None:
    """
    Render the simulator page.

    Assumptions across the first row, the live scenario as a band beneath
    them, then the scenario list and its results side by side.
    """
    baseline = load_baseline()

    _initialize_simulator_state(baseline)
    inject_tooltip_overlay()

    render_top_view(button_text="Back to Main View", view_type="main")

    # Injected once, up front: the control row's live panel and the rail below
    # share the same row markup.
    st.markdown(scenario_rail_css(), unsafe_allow_html=True)

    _render_controls_row(baseline)
    _render_comparison_and_results(baseline)
