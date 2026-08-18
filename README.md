# CLUE

Research repo for the CLUE study: a metric-understanding tool and the dashboard
used to evaluate it.

- [Link to Overleaf Repo](https://www.overleaf.com/5728589448bfhpdjdxgmxc#fb939f)

## What's here

| Directory | What it is |
|---|---|
| [`baseline_dashboard/`](baseline_dashboard/) | The **Customer Value Dashboard** participants use. Runs in both study conditions. |
| [`demo/`](demo/) | **CLUE** — the metric provenance graph, transformation views, and simulator. |
| [`VLDB 2026 Demo/`](VLDB%202026%20Demo/) | Paper source. |

The two apps share no code. The dashboard links to CLUE by URL only.

## Starting a study session

One command brings up both:

```bash
./run_study.sh
```

- Dashboard → http://localhost:8501
- CLUE → http://localhost:8502

It runs in the foreground; Ctrl-C stops both. `CLUE_URL` is set for you so the
dashboard's "Open in CLUE" links resolve. Override `BASELINE_PORT` / `CLUE_PORT`
if those ports are taken.

First time only, build the dashboard's data source (~80s):

```bash
cd baseline_dashboard && ../.venv/bin/python -m datasource.build
```

### Which condition a link opens

The study is within-subjects — each participant uses the dashboard both with
CLUE available and without. **One deployment serves both**; the condition
travels in the link, so it can't be a process-level switch.

For development:

| URL | Condition |
|---|---|
| http://localhost:8501/?s=dev | CLUE enabled |
| http://localhost:8501/?s=dev-baseline | baseline |
| http://localhost:8501 | baseline (no token) |

For participants, generate counterbalanced links first:

```bash
cd baseline_dashboard
../.venv/bin/python -m study.make_sessions --participants 24 \
    --base-url http://localhost:8501
```

This prints a run sheet (participant × block × condition × link) and writes
`study/sessions.json`. Exactly half the participants meet CLUE first.

Two things worth knowing at session time:

- **The condition is pinned at first page load.** Editing `?s=` in an open tab
  won't switch it — that's deliberate, so a participant can't change condition
  mid-task. Use a fresh tab.
- **Resolution fails closed.** A missing, unknown, or mistyped token yields the
  baseline condition and is logged as such, rather than silently granting CLUE.

Interactions are logged to `baseline_dashboard/logs/events-YYYY-MM-DD.jsonl`.
Dev-token sessions log under participant `DEV`, so exploratory clicks are easy
to filter out of study data.

## Running the apps individually

```bash
cd baseline_dashboard && ../.venv/bin/python -m streamlit run app.py
cd demo             && ../.venv/bin/python -m streamlit run main.py
```

Use `../.venv/bin/python -m streamlit`, not bare `streamlit` — the virtualenv is
not on `PATH`.

## Tests

```bash
cd baseline_dashboard && ../.venv/bin/python -m unittest discover tests
```

134 tests. They redirect their own logging to a temp directory, so running them
never contaminates study data.

## Notes

- `baseline_dashboard/data/` (~546 MB of raw CSV plus generated parquet),
  `study/sessions.json`, and `logs/` are gitignored.
- Full dashboard documentation, including the metric definitions and the
  synthesized fields, is in
  [`baseline_dashboard/README.md`](baseline_dashboard/README.md).
- **Known gap:** CLUE is still built around PLTV, whose components differ from
  the dashboard's 6-Month Customer Value, so following the link lands on a
  related but not identical metric. Worth aligning before the study runs.
