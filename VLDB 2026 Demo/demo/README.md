# CLUE Demo App

This folder contains the Streamlit demo application used in the VLDB demo.

## Quick Start

Run from this directory:

- `python -m pip install streamlit`
- `streamlit run main.py`

## File Guide

### main.py
Entry point for the app.

What it does:
- Configures Streamlit page layout.
- Injects global primary-button style.
- Injects shared app styles from `components/styles.py`.
- Initializes global session state (`active_view`, `search_query`).
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
- Renders app title (`CLUE`).
- Renders metric selector (`st.selectbox`) bound to `search_query`.
- Renders navigation button that switches `active_view`.

Main function:
- `render_top_view(button_text, view_type)`

### components/main_view.py
Main dashboard (non-simulator) view.

What it does:
- Shows overview card, explanation card, provenance card, and transformation card.
- Uses PLTV selection checks (`search_query == "pltv"`) to show content.
- Renders the single-line PLTV chart with Vega-Lite.

Main helpers:
- `_is_pltv_selected()`
- `_build_pltv_trend_values()`
- `_build_pltv_vega_spec()`
- `_render_metric_overview()`
- `_render_ai_explanation()`
- `_render_provenance_view()`
- `_render_transformation_view()`
- `render_main_view()`

### components/simulator_view.py
Simulator workflow view.

What it does:
- Renders goal controls (PLTV step control and sliders).
- Renders strategy recommendation panel.
- Renders simulation output panel.
- Manages simulator state in session.

Main helpers:
- `_initialize_simulator_state()`
- `_get_suggestion_texts()`
- `_render_step_slider()`
- `_render_goal_controls()`
- `_render_suggested_fixes_panel()`
- `_render_simulation_output_panel()`
- `render_simulator_view()`

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
- `search_query`: selected metric from top selector
- `show_suggestions`: toggles recommendation list visibility
- `checked_suggestions`: selected suggestion map
- `simulation_started`: controls output panel behavior
- `pltv`, `pltv_input`: PLTV step control values

## Where To Edit What

- Change navigation behavior: `main.py`, `components/top_view.py`
- Change main dashboard cards/chart/text: `components/main_view.py`
- Change simulator controls or simulation flow: `components/simulator_view.py`
- Change visual style/theme/spacing: `components/styles.py`
