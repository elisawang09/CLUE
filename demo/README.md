# CLUE Demo App

This folder contains the Streamlit demo application used in the VLDB demo.

## The metric

CLUE explains **6-Month Customer Value**: the average value generated per acquired user during
the first 6 months after acquisition. It is observed history, not a prediction.

```text
6-Month Customer Value
  = 6-Month Purchase Conversion Rate   (Purchasing Customers / Acquired Users)
  x Orders per Purchasing Customer     (Total Orders / Purchasing Customers)
  x Average Order Value                (Total Gross Order Value / Total Orders)
```

Two time windows are involved and are never merged: the *reference acquisition period* decides
which users are in the group, and the *six-month observation window* runs from each user's own
acquisition date.

## Quick Start

Run from this directory:

- `python -m pip install streamlit`
- `streamlit run main.py`

Numbers come from the modeled data source the baseline dashboard builds
(`baseline_dashboard/data/modeled/`). Without it, CLUE falls back to the spec's reference example
and says so in the overview card.

## File Guide

### data/metrics.py
Single source of every number CLUE displays.

What it does:
- Pins the reference acquisition period and the 6-month observation window.
- Computes the four base counts and the three factors from the modeled tables.
- Runs the consistency checks the main view surfaces as a banner.
- Falls back to the reference example when the data source is missing.

Main helpers:
- `compute_baseline()` / `load_baseline()` (cached)
- `run_checks(baseline)` / `failed_checks(baseline)`
- `node_values(baseline)` — formatted value per provenance node id
- `money()`, `percent()`, `count()`, `decimal()`

### data/graph_data.py
Provenance node/edge model, transformation flows, and simulation deltas.

What it does:
- Defines the provenance graph (`NODES`, `EDGES`, `LEAF_IDS`) with clipped-stem node ids:
  `cust_val`, `conv_rate`, `orders_per_cust`, `avg_order_val`, `acq_users`, `purch_cust_1/_2`,
  `tot_orders_1/_2`, `tot_gross_val`.
- Builds one transformation flow per leaf; four of them share `_acquisition_stage()`, the
  acquisition-group pipeline through to qualifying orders.
- Splits the wording by element: a node's `description` says what that table or column *is*,
  an edge's `label` names the kind of operation ("Filter applied", "Join") and its
  `description` carries the predicate, shown when hovering the operation chip.
- `simulation_deltas()` propagates an illustrative scenario from the historical baseline
  without modifying it.

### main.py
Entry point for the app.

What it does:
- Configures Streamlit page layout.
- Injects global primary-button style.
- Injects shared app styles from `components/styles.py`.
- Initializes global session state (`active_view`).
- Routes to either:
  - `render_main_view()`
  - `render_simulator_view()`

Main functions:
- `_inject_primary_button_style()`
- `_initialize_session_state()`
- `_render_active_view()`
- `main()`

### components/top_view.py
Shared top bar used by both views.

What it does:
- Renders app title (`CLUE`) and the metric being explained (`PRIMARY_METRIC`).
- Renders navigation button that switches `active_view`.

There is no metric selector: participants arrive from the baseline dashboard with the metric
already chosen, and CLUE explains one metric. The dashboard's `?metric=` parameter is accepted
and ignored, so no link lands on an empty page.

Main function:
- `render_top_view(button_text, view_type)`

### components/main_view.py
Main dashboard (non-simulator) view.

What it does:
- Shows overview card, explanation card, provenance card, and transformation card.
- Shows content when the selected metric is `PRIMARY_METRIC` (6-Month Customer Value).
- Renders the value-accumulation chart (cumulative value per acquired user across age months
  1-6, ending on the headline) with Vega-Lite.
- Surfaces failed consistency checks as an error banner.

Main helpers:
- `_is_customer_value_selected()`
- `_build_accumulation_values()`
- `_build_accumulation_vega_spec()`
- `_render_metric_overview()`
- `_render_ai_explanation()`
- `_render_provenance_view()`
- `_render_transformation_view()`
- `_report_checks()`
- `render_main_view()`

### components/simulator_view.py
Simulator workflow view.

What it does:
- Puts the goal, the three assumptions and the scenario readout across the first row, so every
  control is visible without scrolling; Scenario Starters and results run full width below.
- Shows the historical baseline and a planning goal (how much more value users acquired over
  the next 3 months should generate in their first 6 months).
- Renders the three assumptions as free-moving sliders — conversion rate, orders per purchasing
  customer, average order value — seeded at their observed values. They do not rebalance each
  other; the scenario is free to land above or below the goal.
- Lists Scenario Starters computed from whatever the controls currently say; ticking one shows
  what it would imply and feeds the results.
- Renders the results as scenario assumptions → computed consequences → scenario result,
  followed by the propagation graph.

Main helpers:
- `_initialize_simulator_state()`
- `_render_step_slider()` — the planning goal
- `_render_controls_row()`, `_render_scenario_readout()`
- `_render_scenario_starters_panel()`, `selected_starters()`, `scenario_to_simulate()`
- `_assumption_lines()`, `_consequence_lines()`, `_result_lines()`
- `_render_simulation_output_panel()`
- `render_simulator_view()`

### data/scenario.py
Hypothetical scenario state, kept apart from observed history.

What it does:
- `Scenario` holds the three assumptions; purchasing customers, orders, gross value and the
  headline are propagated from them, so the spec's identities hold by construction.
- `from_baseline()`, `goal_value()`, `starters()` (one per lever, computed from the scenario
  currently in the controls, fixed order, never ranked), `combine()`, `run_scenario_checks()`.
- Never writes to `BaselineMetrics` — changing an assumption cannot disturb the numbers the
  main view shows.

### utils/slider_calculations.py
Session-state plumbing for the scenario controls: `initialize_scenario_state()`,
`current_scenario()`, `load_scenario()`, `slider_bounds()`, `uplift_percent()`.

### components/styles.py
Global style system and small HTML helpers.

What it does:
- Builds and injects app-wide CSS (backgrounds, cards, sliders, typography, button tweaks).
- Provides helper for rendering bullet details in custom HTML boxes.

Main helpers:
- `_build_app_css()`
- `inject_checkbox_styles()`
- `inject_app_styles()`
- `_bullets_to_html_list(content)`
- `get_detail_box_html(content)`
- `get_selected_text_style()`
- `get_checkbox_label_html(label, is_selected=False)`

## Session State Keys

Common keys used in the app:
- `active_view`: `main` or `simulator`
- `selected_node`: provenance leaf whose transformation flow is shown
- `show_starters`: toggles the Scenario Starters list
- `simulation_started`: controls output panel behavior
- `sim_uplift`, `sim_uplift_input`: planning goal, as a % above the historical baseline
- `sim_conversion`, `sim_orders_per_cust`, `sim_order_value`: the three scenario assumptions

## Where To Edit What

- Change navigation behavior: `main.py`, `components/top_view.py`
- Change main dashboard cards/chart/text: `components/main_view.py`
- Change the metric definition, reference period, or checks: `data/metrics.py`
- Change provenance nodes or transformation flows: `data/graph_data.py`
- Change scenario propagation or Scenario Starters: `data/scenario.py`
- Change simulator controls or simulation flow: `components/simulator_view.py`
- Change visual style/theme/spacing: `components/styles.py`
