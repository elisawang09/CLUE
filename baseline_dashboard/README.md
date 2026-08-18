# Customer Value Dashboard

A conventional BI dashboard where participants understand a metric and inspect
the data behind it using only ordinary affordances: metric details, calculation
expressions, view underlying data, CSV export.

It runs in **two study conditions**, differing in exactly one thing: whether a
card's ⋯ menu offers **Open in CLUE**, a link into the treatment app in
[`../demo`](../demo). Everything else — filters, cards, charts, dialogs, export —
is identical in both. This app imports nothing from `demo/`; the two talk only
over a URL.

## Quick start

```bash
cd baseline_dashboard
python -m datasource.build      # once, ~80s — builds the modeled data source
streamlit run app.py
```

Or bring up both apps together:

```bash
./run_study.sh                  # baseline on :8501, CLUE on :8502
```

Dependencies are already in the repo's `.venv` (streamlit, pandas, numpy,
altair, pyarrow). Nothing new was added.

```bash
python -m unittest discover tests      # 128 tests
```

## Running a study session

The study is within-subjects: every participant uses both conditions in a
counterbalanced order. One deployment serves both — the condition travels in the
link, not in an environment variable, so a single hosted instance can serve
different participants different conditions at the same time.

Generate links first:

```bash
python -m study.make_sessions --participants 24 --base-url https://<host>
```

This writes `study/sessions.json` (gitignored — participant assignment data) and
prints a run sheet:

```
Participant Block  Condition  Link
P01         1      CLUE       https://<host>/?s=d3d47a
P01         2      baseline   https://<host>/?s=b99d92
P02         1      baseline   https://<host>/?s=f95e31
...
```

Exactly half the participants meet CLUE first. That is counterbalancing, not
plain randomization: with a small sample, random assignment can easily land 9:3
and leave order confounded with condition, with no way to separate them
afterwards.

Tokens are opaque so nothing in the address bar tells a participant which
condition they are in — a visible `?clue=on` would be a demand characteristic.
Resolution **fails closed**: a missing, unknown, or edited token yields the
baseline condition and is logged as such, so a broken link degrades to control
rather than silently granting CLUE. The condition is also pinned at first load,
so editing the URL mid-task cannot switch it.

### Development access

Two memorable tokens for inspecting the dashboard without looking up a
participant link:

| URL | Condition |
|---|---|
| `http://localhost:8501/?s=dev` | CLUE enabled |
| `http://localhost:8501/?s=dev-baseline` | baseline |
| `http://localhost:8501` | baseline (no token — fails closed) |

They are defined in `study/session.py`, not in the registry, so regenerating
`sessions.json` can't wipe them and they never appear in a participant run
sheet. `make_sessions.py` also excludes them when generating tokens.

Dev sessions log under participant `DEV` (`Session.is_dev`), so exploratory
clicks are trivially filtered out of study data rather than sitting there
looking like a real participant.

Note the condition is **pinned at first page load** — editing `?s=` in an open
tab won't switch it. Use a fresh tab or reload.

### Interaction logs

Every interaction appends a JSON line to `logs/events-YYYY-MM-DD.jsonl`
(gitignored):

```json
{"timestamp": "...", "action": "open_details", "participant": "P01",
 "block": 1, "condition": "clue", "token": "d3d47a",
 "metric": "customer_value", "source": "card_menu"}
```

Actions logged: `session_start`, `filter_period`, `filter_window`,
`open_details`, `open_underlying`, `metric_drill`, `underlying_grain`,
`chart_select`, `csv_export`.

Only real interactions are recorded — Streamlit re-runs the whole script on
every widget change, so anything logged on the render path would produce
thousands of duplicates. `underlying_grain` fires once when the panel opens
(recording which grain the metric defaulted to) and again on each real switch.

The test suite redirects logging to a temp directory, so running it never
contaminates study data.

Set `CLUE_URL` when CLUE isn't on `localhost:8502`; `run_study.sh` does it for
you. If CLUE is unreachable the menu item renders disabled with a hint rather
than as a dead link.

## The metric

**6-Month Customer Value** — average value generated per acquired user during
the first 6 months after acquisition.

```
6-Month Customer Value
  = 6-Month Purchase Conversion Rate
  × Orders per Purchasing Customer
  × Average Order Value

  = Total Gross Order Value ÷ Acquired Users
```

Two filters, answering different questions:

- **Reference Acquisition Period** — *which* users are included (default Jan–Mar 2022)
- **Observation Window** — *how long* each is observed after their **own**
  acquisition date (3/6/9/12 months, default 6)

The second matters more than it looks. Orders are never filtered by calendar
date; a user acquired on 20 February is observed from 20 February. Filtering
orders by the reference period instead would give later-acquired users a shorter
window and quietly understate the metric.

`customer_age_month` is therefore anniversary-based: month *k* covers
`[acquisition + (k−1) months, acquisition + k months)`, clamped at month ends the
same way `pd.DateOffset` clamps.

Four consistency checks run at load and after every filter change. If the
headline ever disagrees with its components or with the charts, the dashboard
says so in a banner rather than showing a plausible wrong number.

## Layout

```
Customer Value Dashboard · E-commerce Growth Overview
[Reference Acquisition Period]  [Observation Window]

6-Month Customer Value | Conversion Rate | Orders/Purchasing Customer | AOV | Acquired Users

[ Customer Value in the First 6 Months ]  [ Monthly Value Contribution ]
```

Both charts are drawn from a single monthly series, so the cumulative line is
always the running sum of the contribution bars. Month 6 of the line equals the
headline; the bars sum to it.

Cards carry no sparklines or deltas: the metric describes one acquisition cohort
observed over its own first months, so a calendar-time sparkline would imply a
trend the number does not have.

## Data

`data/` holds the raw jaffle-shop CSVs (~546 MB, gitignored) and the modeled
Parquet the app actually reads.

| Raw file | Rows |
|---|---:|
| `raw_customers.csv` | 3,102 |
| `raw_orders.csv` | 2,088,006 |
| `raw_order_items.csv` | 3,024,215 |
| `raw_products.csv` | 10 |
| `raw_supplies.csv` | 65 |
| `raw_stores.csv` | 6 |

`gross_value = revenue − cost`, where revenue is the product's list price and
cost is the sum of its supply lines. Money is in cents in the raw data and
converted to dollars once, during the build.

### Synthesized

Three things the raw data cannot supply, all deterministic (seeded from a hash of
the customer id, so every run and every participant sees identical numbers) and
documented in `data/modeled/SYNTHESIZED.md`:

1. **Time shift, +1400 days.** Moves the final order to 2026-06-30 so the data
   reads as current. Exactly 200 weeks, so every order keeps its day of week —
   this business has a strong weekly rhythm. Subtract 1400 days to recover
   original dates.
2. **`account_created_at`** = first order − a signup lag drawn from four 15-day
   buckets at 0.30 / 0.30 / 0.25 / 0.15.
3. **Non-purchasing acquired users.** Every customer in the raw data has orders,
   so conversion would be exactly 100% for every cohort and the headline would
   collapse to Orders × AOV. Signup-only users were generated per cohort month at
   a conversion rate drawn in 30–50%, making the 3,102 real purchasers ~40% of
   7,779 acquired users.

Orders, order lines, prices and supply costs are all real.

## Why the build step exists

546 MB of CSV takes ~40 s to parse, and Streamlit re-runs the script on every
interaction. But the answer also cannot be one precomputed number, because the
filters are interactive.

So: **precompute the shape, compute the ratios on demand.**

- **Build once** → five Parquet files in `data/modeled/`.
- **Two small tables** serve every KPI and both charts: `customers.parquet`
  (7,779 rows) and `customer_age_facts.parquet` (34,515 rows). Aggregating ~42 K
  rows is milliseconds, for any filter combination.
- **`@st.cache_data`** on the loaders and the filtered aggregate.

The 2 M-row `orders` and 3 M-row `order_items` tables are touched *only* by the
order-level underlying-data view, filtered and paginated, and only when someone
opens it.

## Files

```
app.py                       page config, state, layout, dialog dispatch
clue.py                      CLUE URL, metric mapping, reachability probe
study/
  session.py                 condition assignment from the link token
  make_sessions.py           counterbalanced link generator
  events.py                  interaction logging
datasource/
  age.py                     time shift + customer_age_month
  synthesize.py              signup lag, non-purchasing users
  build.py                   raw CSV → modeled parquet
  schema.py                  expected columns + readable errors
  loader.py                  cached parquet readers
metrics/
  registry.py                names, descriptions, expression tokens, formats
  compute.py                 (period, window) → KPIs + both chart series
  checks.py                  the four consistency assertions
components/
  styles.py header.py filters.py kpi_cards.py charts.py
  metric_details.py          dialog + component drill navigation
  underlying_data.py         Summary / Underlying rows + CSV export
tests/                       128 unittest tests
```

## Where to edit what

- **Metric wording, descriptions, formulas** — `metrics/registry.py`
- **How a metric is calculated** — `metrics/compute.py`
- **Filter defaults** — `components/filters.py`
- **Colors, typography, card styling** — `components/styles.py`
- **Chart marks and axes** — `components/charts.py`
- **Drilldown columns** — `components/underlying_data.py`
- **Anything about the raw → modeled transform** — `datasource/build.py`
  (re-run the build afterwards)
- **Which cards link into CLUE** — `MetricDef.clue_metric` in
  `metrics/registry.py`; only `customer_value` is mapped today
- **What gets logged** — `study/events.py` and the `log_event` call sites

## Known gap

CLUE is still built around **PLTV** (`Probability of Active × Expected # Orders ×
Expected Order Value`), whose components differ from this dashboard's 6-Month
Customer Value. A participant following the link lands on a related but not
identical metric. Realigning it means rewriting `demo/data/graph_data.py`'s
nodes, simulation deltas, and transformation flows — worth doing before the
study runs.
