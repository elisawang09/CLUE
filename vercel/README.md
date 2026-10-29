# CLUE on Vercel

A static port of the two Streamlit apps, deployed to Vercel as one site.
Streamlit needs a long-running server, which Vercel doesn't offer, so this
folder restates both apps in plain HTML and JavaScript. There's no build step.

| URL | App | Original |
|---|---|---|
| `/` | Customer Value Dashboard | [`baseline_dashboard/`](../baseline_dashboard/) |
| `/clue/` (main view), `/clue/#simulator` | CLUE | [`demo/`](../demo/) |

## Deploy

```bash
cd baseline_dashboard && ../.venv/bin/python -m datasource.build   # once: raw CSV -> parquet
cd .. && .venv/bin/python vercel/scripts/export_data.py            # parquet -> vercel/public/data/
```

Then do one of the following:

- **Git:** import the repo in Vercel, set **Root Directory** to `vercel`, and
  commit `vercel/public/data/`.
- **CLI:** run `cd vercel && npx vercel --prod`. The CLI uploads local files,
  so you don't need to commit the data.

To preview locally, run `python3 -m http.server 8000 -d vercel/public` and open
http://localhost:8000/?s=dev.

## How the data gets here

```
baseline_dashboard/data/raw_*.csv
  └─ datasource/build.py                  (unchanged, still Python)
     └─ data/modeled/*.parquet
        └─ vercel/scripts/export_data.py
           ├─ public/data/cohorts.json       ← metrics/compute.py · month_table()
           └─ public/data/months/YYYY-MM.json ← rows for View Underlying Data
```

`cohorts.json` holds four counts per acquisition month: acquired users,
purchasing customers, total orders and total gross order value. Every card,
chart bar and CLUE figure is a ratio or sum of these. The export calls the
dashboard's own `month_table()`, so the numbers can't drift from the Streamlit
app.

## Dashboard: element → file → original

Paths in the last column are relative to `baseline_dashboard/`.

| Element | Here (`public/`) | Original |
|---|---|---|
| Page setup and update loop | `assets/dashboard.js` · `main()`, `update()` | `app.py` · `main()` |
| Title and subtitle | `index.html` `<header>` | `components/header.py` · `render_header()` |
| Reference Acquisition Period filter | `dashboard.js` · `renderFilters()`, `cohortRange()` | `components/filters.py` · `render_filters()` |
| Default period (Jan–Jun 2024) | `assets/common.js` · `DEFAULT_START`, `DEFAULT_END` | `components/filters.py` · `DEFAULT_START`, `DEFAULT_END` |
| Ratios and headline per month | `dashboard.js` · `derive()` | `metrics/compute.py` · `_derive()` |
| Latest month and previous month | `dashboard.js` · `compute()` | `metrics/compute.py` · `compute()` |
| Month-over-month change | `dashboard.js` · `delta()`, `deltaRatio()` | `metrics/compute.py` · `CohortMetrics.delta()`, `delta_ratio()` |
| Consistency-check banner | `dashboard.js` · `runChecks()`, `reportChecks()` | `metrics/checks.py` · `run_checks()`; `app.py` · `_report_checks()` |
| Card names, descriptions, formats | `dashboard.js` · `METRICS` | `metrics/registry.py` · `METRICS` |
| Number formatting | `common.js` · `money()`, `percent()`, `count()`, `decimal()` | `metrics/registry.py` · same names |
| Five KPI cards | `dashboard.js` · `renderCards()` | `components/kpi_cards.py` · `render_kpi_cards()` |
| ▲/▼ change line | `dashboard.js` · `deltaHtml()`, `formatDelta()` | `components/kpi_cards.py` · `_delta_html()`, `_format_delta()` |
| ⋯ card menu | `dashboard.js` · `menuHtml()`, `wireMenus()` | `components/kpi_cards.py` · `_render_menu()` |
| Selected-card outline | `assets/dashboard.css` · `.bd-kpi.is-selected` | `components/styles.py` · `highlight_selected_card()` |
| Open in CLUE ↗ link | `dashboard.js` · `clueUrl()` | `clue.py` · `clue_url_for()` |
| Condition from `?s=` | `dashboard.js` · `resolveSession()` | `study/session.py` · `lookup()`, `resolve_session()` |
| Two column charts | `dashboard.js` · `chartSpec()`, `renderChart()` | `components/charts.py` · `_column_chart()` |
| Chart click → selected month | `dashboard.js` · `pickedMonth()` | `components/charts.py` · `_selected_month()` |
| View Underlying Data dialog | `dashboard.js` · `openUnderlying()` | `components/underlying_data.py` · `render_underlying_data()` |
| Summary tab | `dashboard.js` · `summaryHtml()` | `components/underlying_data.py` · `period_summary()`; `charts.py` · `month_summary()` |
| Underlying rows tab | `dashboard.js` · `renderRows()` | `components/underlying_data.py` · `_render_rows()` |
| Customer and order rows | `vercel/scripts/export_data.py` · `month_files()` (outside `public/`) | `components/underlying_data.py` · `customer_rows()`, `order_rows()` |
| Lazy row loading | `common.js` · `loadMonthRows()` | `datasource/loader.py` · `load_orders()` |
| Footer caption | `dashboard.js` · `update()` | `app.py` · `st.caption(...)` |
| Colours, cards, typography | `assets/dashboard.css` | `components/styles.py` |

**Not ported:**
- `datasource/` still runs in Python, ahead of the export.
- `study/events.py` (logging) and `study/make_sessions.py` (participant links)
  don't apply on a static host.
- `clue.py` · `is_clue_running()` isn't needed, because CLUE is on the same
  site.

## CLUE: element → file → original

Paths in the last column are relative to `demo/`.

| Element | Here (`public/`) | Original |
|---|---|---|
| View switch (main ↔ simulator) | `assets/clue.js` · `render()`, `topBar()` | `main.py`; `components/top_view.py` |
| Reference period from the link | `assets/clue-model.js` · `referencePeriod()` | `data/metrics.py` · `reference_period()` |
| Historical baseline | `clue-model.js` · `computeBaseline()` | `data/metrics.py` · `compute_baseline()` |
| Future cohort size | `clue-model.js` · `futureAcquiredUsers()` | `data/metrics.py` · `_future_acquired_users()` |
| Fallback example (no data) | `clue-model.js` · `fallbackBaseline()` | `data/metrics.py` · `_fallback_baseline()` |
| Consistency checks | `clue-model.js` · `failedChecks()` | `data/metrics.py` · `run_checks()` |
| Metric Overview chart | `clue.js` · `overviewChartSpec()` | `components/main_view.py` · `_build_chart_vega_spec()` |
| AI-Generated Explanation | `clue.js` · `renderMainView()` | `components/main_view.py` · `_render_ai_explanation()` |
| Provenance nodes and edges | `clue-model.js` · `NODES`, `EDGES`, `LEAF_IDS` | `data/graph_data.py` |
| Provenance graph | `assets/clue-graphs.js` · `renderProvenanceGraph()` | `components/provenance_graph.py`; `utils/graph_builders.py` |
| Path highlight | `clue-model.js` · `ancestorsOf()` | `utils/graph_utils.py` · `ancestors_of()` |
| Transformation flows | `clue-model.js` · `transformationFlow()` | `data/graph_data.py` · `transformation_flow()` |
| Transformation graph | `clue-graphs.js` · `renderTransformationGraph()` | `utils/graph_builders.py` · `build_transformation_flow_elements()` |
| Node colours and legends | `clue-graphs.js` · `COLORS`, `*LegendHtml()` | `utils/graph_styles.py` |
| Hover tooltip | `common.js` · `installTooltip()` | `utils/tooltip_overlay.py` |
| Scenario maths | `clue-model.js` · `scenario()`, `fromBaseline()`, `fromObservedBest()`, `goalValue()` | `data/scenario.py` |
| Goal stepper and sliders | `clue.js` · `goalHtml()`, `sliderHtml()`, `sliderBounds()` | `components/simulator_view.py` · `_render_controls_row()`; `utils/slider_calculations.py` |
| Live scenario band and pin | `clue.js` · `stripHtml()` | `components/simulator_view.py` · `_render_scenario_strip()` |
| Scenario list | `clue.js` · `comparisonCards()`, `scenarioListHtml()` | `components/simulator_view.py` · `comparison_cards()`, `_render_scenario_list()` |
| Simulation results | `clue.js` · `resultsHtml()` | `components/simulator_view.py` · `_render_results_column()` |
| Simulation graph deltas | `clue-model.js` · `simulationDeltas()`; `clue-graphs.js` · `renderSimulationGraph()` | `data/graph_data.py` · `simulation_deltas()`; `components/simulation_result_graph.py` |
| Styles and icons | `assets/clue.css`; `static/*.png` | `components/styles.py`; `static/` |

## Links and conditions

| URL | Condition |
|---|---|
| `/?s=dev` | CLUE enabled (⋯ menu shows **Open in CLUE ↗**) |
| `/?s=dev-baseline`, `/`, any other token | baseline |

The handoff link looks like
`/clue/?metric=90-Day+Customer+Value&start=2024-01&end=2024-06&s=dev`.

Participant tokens and logging are deliberately left out. Publishing
`sessions.json` on a public site would reveal every assignment, and Vercel has
no disk to append logs to. Run study sessions on the Streamlit apps.

## Changing things

Change the Python first, then the matching row above. If a metric's
definition changes, re-run the build and the export.
