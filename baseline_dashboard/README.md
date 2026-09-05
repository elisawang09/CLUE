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

Actions logged: `session_start`, `filter_period`, `open_underlying`,
`underlying_grain`, `chart_select`.

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

**90-Day Customer Value** — average value generated per acquired user during
their first 90 days after acquisition.

```
90-Day Customer Value
  = 90-Day Purchase Conversion Rate
  × Orders per Purchasing Customer
  × Average Order Value

  = Total Gross Order Value ÷ Acquired Users
```

One filter: **Reference Acquisition Period**, which decides *which* users are
included (default Jan–Jun 2024, the most recent year in the data; July is a
3-user stub month and is left out of the default). How long each is observed is no longer a
control — the window is fixed at 90 days from each user's **own** acquisition
date.

That per-user anchoring matters more than it looks. Orders are never filtered by
calendar date; a user acquired on 20 February is observed from 20 February.
Filtering orders by the reference period instead would give later-acquired users
a shorter window and quietly understate the metric.

`customer_age_day` is the derivation everything is filtered on: day 0 is the
acquisition day, so the first 90 days are offsets 0–89. It is date-granular, so
the boundary falls at midnight rather than at the acquisition time of day.

Consistency checks run at load and after every filter change, covering both the
headline against its own factors and every charted month against the same two
identities. If they ever disagree, the dashboard says so in a banner rather than
showing a plausible wrong number.

## Layout

```
Customer Value Dashboard · E-commerce Growth Overview
[Reference Acquisition Period]

90-Day Customer Value | Conversion Rate | Orders/Purchasing Customer | AOV | Acquired Users
     each naming its acquisition month, with ▲/▼ change vs the month before

[ 90-Day Customer Value      ]  [ 90-Day Purchase Conversion Rate ]
[   by Acquisition Month     ]  [   by Acquisition Month          ]
```

**Cards report one month; charts report the range.** The cards show the *most
recent acquisition month* in the reference period — with Jan–Jun 2024 selected,
they describe Jun 2024 — and each card names that month above its value. View
Underlying Data follows the same month, so a participant checking the number by
hand reconciles against the cohort the card actually describes.

The comparison is against the month immediately preceding **in the data**, not
in the selection, so narrowing the filter to a single month still shows a
change. The earliest cohort in the data has no previous month and renders no
delta rather than a fabricated zero.

Both charts are vertical column charts over acquisition months, drawn from the
same per-month table the cards read, so a bar and a card cannot disagree about
the same month. The month the cards report is drawn in the accent colour and the
rest are muted — that emphasis is the only thing connecting the cards to the
bars. Past 12 months in range, per-bar labels are dropped and axis labels angle,
because the period can span the whole dataset.

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
2. **`account_created_at`** = first order − a signup lag drawn from seven
   buckets spanning 0–269 days. The tail past day 90 is deliberate and carries
   15% of purchasers: with every purchaser converting inside the window, the
   90-day observation window would exclude nobody and 90-day conversion would be
   lifetime conversion under another name.
3. **Non-purchasing acquired users.** Every customer in the raw data has orders,
   so conversion would be exactly 100% for every cohort and the headline would
   collapse to Orders × AOV. Signup-only users are generated per cohort month
   against a target conversion rate that is a *function of the month* — level,
   secular trend, annual seasonal term peaking in November, small jitter. An
   earlier version drew each month independently in a fixed range, which made
   the per-cohort-month conversion chart pure noise: with one bar per month
   there was no shape to read because there was none to find.

Orders, order lines, prices and supply costs are all real.

### Incomplete cohort months, excluded

Acquisition months earlier than the first observed order are dropped at build
time. Signup is derived by subtracting a lag from the first order, so those
months can only ever contain long-lag purchasers — a biased sample missing every
fast converter, whose 90-day conversion collapses toward zero for reasons that
have nothing to do with the business. This removes 9 months and ~5% of users,
and leaves 49 clean acquisition months from 2020-07 to 2024-07.

## Why the build step exists

546 MB of CSV takes ~40 s to parse, and Streamlit re-runs the script on every
interaction. But the answer also cannot be one precomputed number, because the
filters are interactive.

So: **precompute the shape, compute the ratios on demand.**

- **Build once** → six Parquet files in `data/modeled/`.
- **Two small tables** serve every KPI and both charts: `customers.parquet`
  (7,137 rows) and `customer_window_facts.parquet` (2,527 rows, one per user who
  ordered inside their own 90 days). Aggregating ~10 K rows is milliseconds, for
  any filter.
- The old month-grain `customer_age_facts` table is gone. 90 days is not three
  anniversary months, so a month-grain table cannot express the window, and once
  CLUE moved onto the same 90-day definition nothing read it at all. The
  `customer_age_month` column stays on `orders` — it costs one int64 per row and
  is the natural way to read an order row by hand.
- **`@st.cache_data`** on the loaders and the filtered aggregate.

The 2 M-row `orders` and 3 M-row `order_items` tables are touched *only* by the
order-level underlying-data view, filtered and paginated, and only when someone
opens it.

The card menu holds View Underlying Data (and, in the CLUE condition, Open in
CLUE). The Metric Details / calculation drill-down panel and the CSV export were
both removed; the underlying tables are read on screen and not taken away.

## Files

```
app.py                       page config, state, layout, dialog dispatch
clue.py                      CLUE URL, metric mapping, reachability probe
study/
  session.py                 condition assignment from the link token
  make_sessions.py           counterbalanced link generator
  events.py                  interaction logging
datasource/
  age.py                     time shift + customer_age_month/_days
  synthesize.py              signup lag, non-purchasing users
  build.py                   raw CSV → modeled parquet
  schema.py                  expected columns + readable errors
  loader.py                  cached parquet readers
metrics/
  registry.py                names, descriptions, expression tokens, formats
  compute.py                 period → per-month table, KPIs, both charts
  checks.py                  the four consistency assertions
components/
  styles.py header.py filters.py kpi_cards.py charts.py
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

## The handoff to CLUE

"Open in CLUE" carries three things: the metric name, the reference acquisition
period, and the session token. CLUE applies the same rule the cards do — the
headline describes the *last month in the period* — so both apps explain the
same cohort and the same number. A participant who narrows the filter and then
clicks through sees what they were looking at, not a pinned default.

CLUE's own test suite asserts the two agree, factor for factor and bar for bar,
across more than one period.
