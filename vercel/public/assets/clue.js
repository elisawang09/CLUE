// CLUE page: main view and #simulator. Port of demo/main.py; ?metric= is ignored, ?start/?end pick the cohort.

import {
  DataMissingError,
  count,
  decimal,
  html,
  installTooltip,
  loadCohorts,
  money,
  percent,
  raw,
  wholeMoney,
} from "./common.js";
import {
  DEFAULT_UPLIFT_PERCENT,
  PRIMARY_METRIC,
  computeBaseline,
  failedChecks,
  fallbackBaseline,
  fromBaseline,
  fromObservedBest,
  goalValue,
  nodeValues,
  observedRange,
  referencePeriod,
  scenario,
  simulationDeltas,
} from "./clue-model.js";
import {
  provenanceLegendHtml,
  renderProvenanceGraph,
  renderSimulationGraph,
  renderTransformationGraph,
  transformationLegendHtml,
} from "./clue-graphs.js";

const app = document.getElementById("app");

// Scenario list slots, including "Best observed" (slider_calculations.py · MAX_RAIL_CARDS).
const MAX_RAIL_CARDS = 6;
const UPLIFT_MIN = 0;
const UPLIFT_MAX = 100;
const UPLIFT_STEP = 5;
const REFERENCE_CARD_ID = "__reference__";
const CURRENT_CARD_ID = "__current__";

const state = {
  baseline: null,
  selectedNode: null,
  // Simulator inputs, seeded from the baseline on first visit.
  sim: null,
  pinned: [],
  selectedCard: CURRENT_CARD_ID,
  showReferenceCard: true,
};

// == Shared chrome · components/top_view.py, main_view.py · _report_checks()

function topBar(buttonText, view) {
  return html`
    <header class="clue-top">
      <h1>CLUE</h1>
      <p class="clue-top-metric">${PRIMARY_METRIC}</p>
      <button type="button" class="clue-button is-primary" data-view="${view}">${buttonText}</button>
    </header>`;
}

function checksHtml(baseline) {
  const failed = failedChecks(baseline);
  const banner = failed.length
    ? html`<div class="clue-error" role="alert">
        <strong>Metric consistency check failed — these numbers should not be used:</strong>
        <ul>${failed.map((c) => html`<li><b>${c.name}</b> — ${c.detail}</li>`)}</ul>
      </div>`
    : "";
  const fallback = baseline.isFallback
    ? html`<p class="clue-caption">Modeled data source not found — showing the reference
        example figures. Build it with <code>python -m datasource.build</code> from
        <code>baseline_dashboard/</code>, then export it with
        <code>vercel/scripts/export_data.py</code>.</p>`
    : "";
  return html`${banner}${fallback}`;
}

function wireViewSwitch() {
  app.querySelectorAll("[data-view]").forEach((button) =>
    button.addEventListener("click", () => {
      location.hash = button.dataset.view === "simulator" ? "simulator" : "";
    })
  );
}

// == Main view · components/main_view.py

function overviewChartSpec(baseline) {
  const values = baseline.byMonth.map((point) => ({
    month: point.month_label,
    value: Math.round(point.customer_value * 100) / 100,
    is_focus: point.is_focus,
  }));
  const ceiling = Math.max(...values.map((v) => v.value), 0) * 1.2 || 1;
  const x = {
    field: "month",
    type: "ordinal",
    sort: null,
    axis: {
      title: "User Acquisition Month",
      labelAngle: values.length <= 8 ? 0 : -45,
      labelColor: "#7B7F87",
      titleColor: "#7B7F87",
      grid: false,
    },
  };
  const y = {
    field: "value",
    type: "quantitative",
    scale: { domain: [0, ceiling] },
    axis: { title: null, format: "$,.0f", tickCount: 5, labelColor: "#7B7F87", gridColor: "#E5E7EB" },
  };
  // Explained month in the accent colour and labelled; other months muted (_build_chart_vega_spec).
  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    width: "container",
    height: 200,
    autosize: { type: "fit-x", contains: "padding" },
    data: { values },
    layer: [
      {
        mark: { type: "bar", cornerRadiusTopLeft: 4, cornerRadiusTopRight: 4 },
        encoding: {
          x,
          y,
          color: { condition: { test: "datum.is_focus", value: "#2F3E7C" }, value: "#C9CDD3" },
          tooltip: [
            { field: "month", type: "ordinal", title: "User Acquisition Month" },
            { field: "value", type: "quantitative", title: PRIMARY_METRIC, format: "$,.2f" },
          ],
        },
      },
      {
        mark: { type: "text", dy: -8, fontSize: 12, fontWeight: "bold", color: "#111111" },
        encoding: {
          x,
          y,
          text: { field: "value", type: "quantitative", format: "$,.2f" },
          opacity: { condition: { test: "datum.is_focus", value: 1 }, value: 0 },
        },
      },
    ],
    config: { view: { stroke: null } },
  };
}

function renderMainView() {
  const b = state.baseline;
  app.innerHTML = html`
    ${topBar("🚀 Launch Metric Simulator", "simulator")}
    ${checksHtml(b)}
    <div class="clue-main-grid">
      <div class="clue-col">
        <section class="clue-card-panel">
          <h3>Metric Overview</h3>
          <h6>${PRIMARY_METRIC}: ${money(b.customer_value)} per acquired user</h6>
          <div class="clue-overview-chart" id="overview-chart"></div>
        </section>
        <section class="clue-card-panel clue-explanation">
          <h3>AI-Generated Explanation</h3>
          <p><b>${PRIMARY_METRIC}</b> is the average value a newly acquired user generates
            in their first ${b.windowDays} days. Three things decide it:</p>
          <ul>
            <li><b>Purchase conversion</b> — how many of the acquired users buy at all inside that window</li>
            <li><b>Order frequency</b> — how often those customers come back</li>
            <li><b>Average order value</b> — what each order is worth once its costs are taken out</li>
          </ul>
          <p>The three multiply together to give the headline. Every acquired user counts
            toward the average, including those who never order — that is what makes it a
            value <em>per acquired user</em> rather than per customer.</p>
          <p>The figure describes users acquired in <b>${b.cohortLabel}</b>, the most recent
            month in the reference period. The chart above places that month among its
            neighbours.</p>
        </section>
      </div>
      <div class="clue-col">
        <section class="clue-card-panel">
          <h3>Provenance of Metric
            <span class="clue-help" data-tooltip="Click a leaf metric to highlight its computation path from source tables." tabindex="0">?</span>
          </h3>
          ${raw(provenanceLegendHtml())}
          <div id="provenance-graph"></div>
        </section>
        <section class="clue-card-panel">
          <h3>Transformation View
            <span class="clue-help" data-tooltip="Shows how the selected node is computed from raw source tables." tabindex="0">?</span>
          </h3>
          ${raw(transformationLegendHtml())}
          <div id="transformation-graph"></div>
        </section>
      </div>
    </div>`;

  wireViewSwitch();
  if (b.byMonth.length) {
    window.vegaEmbed("#overview-chart", overviewChartSpec(b), { actions: false, renderer: "svg" });
  }
  drawProvenance();
}

function drawProvenance() {
  const b = state.baseline;
  renderProvenanceGraph(document.getElementById("provenance-graph"), {
    highlighted: state.selectedNode,
    values: nodeValues(b),
    onSelect: (id) => {
      if (id === state.selectedNode) return;
      state.selectedNode = id;
      drawProvenance();
    },
  });
  renderTransformationGraph(
    document.getElementById("transformation-graph"),
    state.selectedNode,
    b.cohortLabel
  );
}

// == Simulator state · utils/slider_calculations.py

function initSimulator() {
  if (state.sim) return;
  const b = state.baseline;
  const seed = (value) => (Number.isFinite(value) ? value : 0);
  state.sim = {
    conversion: seed(b.conversion_rate) * 100, // percentage points
    orders: seed(b.orders_per_purchasing_customer),
    orderValue: seed(b.average_order_value),
    uplift: DEFAULT_UPLIFT_PERCENT,
  };
}

// [min, max, step] per slider; max is twice the baseline (slider_bounds).
function sliderBounds(b) {
  const round = (value, digits) => Number((value || 0).toFixed(digits));
  return {
    conversion: [0, 100, 0.5],
    orders: [0, Math.max(round(b.orders_per_purchasing_customer * 2, 1), 0.1), 0.1],
    orderValue: [0, Math.max(round(b.average_order_value * 2, 2), 0.01), 0.01],
  };
}

function currentScenario() {
  const b = state.baseline;
  return scenario(
    state.sim.conversion / 100,
    state.sim.orders,
    state.sim.orderValue,
    b.futureAcquiredUsers
  );
}

// Cards in the scenario list: "Best observed" plus pinned ones (comparison_cards).
function comparisonCards() {
  const b = state.baseline;
  const cards = [];
  if (state.showReferenceCard) {
    cards.push({
      id: REFERENCE_CARD_ID,
      title: "Best observed",
      note: `each factor at its best month in ${b.periodLabel} — a composite, not one actual month`,
      scenario: fromObservedBest(b),
    });
  }
  for (const { name, scenario: pinned } of state.pinned) {
    cards.push({ id: name, title: `Scenario ${name}`, note: "pinned", scenario: pinned });
  }
  return cards;
}

// First unused letter; the original's len(pinned) reused names after a removal.
function nextScenarioName() {
  const used = new Set(state.pinned.map((p) => p.name));
  for (let i = 0; i < 26; i += 1) {
    const name = String.fromCharCode(65 + i);
    if (!used.has(name)) return name;
  }
  return "?";
}

function canPin() {
  return comparisonCards().length < MAX_RAIL_CARDS;
}

// == Simulator view · components/simulator_view.py

function pathwayRows(b, plan) {
  const before = fromBaseline(b);
  return [
    ["Future users", count(plan.acquired_users)],
    ["Purchasing", `${count(before.purchasing_customers)} → ${count(plan.purchasing_customers)}`],
    ["Orders", `${count(before.total_orders)} → ${count(plan.total_orders)}`],
    ["Gross value", `${wholeMoney(before.total_gross_order_value)} → ${wholeMoney(plan.total_gross_order_value)}`],
  ];
}

function changeVsBaseline(b, plan) {
  return b.customer_value ? (plan.customer_value / b.customer_value - 1) * 100 : 0;
}

// Signed one-decimal percent; float noise shows as +0.0, not -0.0.
const signed = (value) => {
  const shown = Math.abs(value) < 0.05 ? 0 : value;
  return `${shown >= 0 ? "+" : ""}${shown.toFixed(1)}`;
};

function observedCaption(b, attribute, fmt) {
  const [low, high] = observedRange(b, attribute);
  return html`<div class="clue-observed-range">${b.periodLabel} range: ${fmt(low)} – ${fmt(high)}</div>`;
}

// Filled share of a slider track, for the WebKit track gradient.
function fillPercent(value, min, max) {
  return max > min ? Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100)) : 0;
}

// Value label per slider.
const SLIDER_DISPLAY = {
  conversion: (value) => `${value.toFixed(1)}%`,
  orders: (value) => value.toFixed(1),
  orderValue: (value) => `$${value.toFixed(2)}`,
};

// One assumption slider. state.sim keeps the exact baseline until moved, even if the thumb snaps.
function sliderHtml(key, title, [min, max, step], caption) {
  const display = SLIDER_DISPLAY[key];
  return html`
    <div class="clue-control">
      <h6>${title}</h6>
      <div class="clue-slider">
        <output class="clue-slider-value" for="slider-${key}" id="value-${key}">${display(state.sim[key])}</output>
        <input type="range" id="slider-${key}" data-key="${key}" min="${min}" max="${max}"
               step="${step}" value="${state.sim[key]}" aria-label="${title}"
               style="--fill: ${fillPercent(state.sim[key], min, max)}%">
        <div class="clue-slider-scale"><span>${display(min)}</span><span>${display(max)}</span></div>
      </div>
      ${caption}
    </div>`;
}

function goalHtml(b) {
  const goal = goalValue(b, state.sim.uplift);
  return html`
    <div class="clue-control">
      <h6>🎯 Extra ${b.windowDays}-day value from users acquired in the next 3 months (%)</h6>
      <div class="clue-stepper">
        <button type="button" class="clue-button is-primary" data-step="-1" aria-label="Decrease goal">−</button>
        <input type="number" id="uplift" min="${UPLIFT_MIN}" max="${UPLIFT_MAX}" step="${UPLIFT_STEP}"
               value="${state.sim.uplift}" aria-label="Uplift over the historical baseline (%)">
        <button type="button" class="clue-button is-primary" data-step="1" aria-label="Increase goal">+</button>
      </div>
      <div class="clue-goal-line" id="goal-line">Historical Baseline: <b>${money(b.customer_value)}</b>
        per acquired user&nbsp;&nbsp;·&nbsp;&nbsp;Goal: <b>${money(goal)}</b></div>
    </div>`;
}

function stripHtml(b) {
  const plan = currentScenario();
  const goal = goalValue(b, state.sim.uplift);
  const gap = plan.customer_value - goal;
  const met = gap >= 0;
  const room = canPin();
  return html`
    <div class="clue-strip-head">
      <div class="clue-card-label">Scenario</div>
      <div class="clue-strip-value">${money(plan.customer_value)}</div>
      <div class="clue-strip-sub">${signed(changeVsBaseline(b, plan))}% vs baseline ·
        ${money(Math.abs(gap))} ${met ? "above" : "below"} goal</div>
    </div>
    <div class="clue-strip-stats">
      ${pathwayRows(b, plan).map(
        ([label, value]) => html`<div class="clue-strip-stat"><div class="clue-card-label">${label}</div><b>${value}</b></div>`
      )}
    </div>
    <div class="clue-strip-action">
      <span class="clue-goal ${met ? "met" : "missed"}">${met ? "✓ meets goal" : "below goal"}</span>
      <button type="button" class="clue-button is-primary" id="pin" ${room ? "" : raw("disabled")}
        ${room ? "" : raw('data-tooltip="Remove a scenario to pin another."')}>
        📌 ${room ? `Pin as Scenario ${nextScenarioName()}` : `List is full (${MAX_RAIL_CARDS} scenarios)`}
      </button>
    </div>`;
}

function assumptionLines(b, plan) {
  const rows = [
    [`${b.windowLabel} Purchase Conversion Rate`, percent, b.conversion_rate, plan.conversion_rate],
    ["Orders per Purchasing Customer", decimal, b.orders_per_purchasing_customer, plan.orders_per_purchasing_customer],
    ["Average Order Value", money, b.average_order_value, plan.average_order_value],
  ];
  const changed = rows
    .filter(([, , before, after]) => Math.abs(after - before) > 1e-9)
    .map(([label, fmt, before, after]) => `${label}: ${fmt(before)} → ${fmt(after)}`);
  return changed.length ? changed : ["Every factor held at its historical baseline value."];
}

function consequenceLines(b, plan) {
  const before = fromBaseline(b);
  return [
    `Future Acquired Users (${b.futurePeriodLabel}): ${count(plan.acquired_users)}`,
    `Purchasing Customers: ${count(before.purchasing_customers)} → ${count(plan.purchasing_customers)}`,
    `Total Orders: ${count(before.total_orders)} → ${count(plan.total_orders)}`,
    `Total Gross Order Value: ${wholeMoney(before.total_gross_order_value)} → ${wholeMoney(plan.total_gross_order_value)}`,
  ];
}

function resultLines(b, plan) {
  const goal = goalValue(b, state.sim.uplift);
  return [
    `${PRIMARY_METRIC}: ${money(b.customer_value)} → ${money(plan.customer_value)}  ` +
      `(${signed(changeVsBaseline(b, plan))}%)`,
    `Goal: ${money(goal)} — the scenario result is ${plan.customer_value >= goal ? "above" : "below"} it.`,
  ];
}

function scenarioListHtml(b, cards, goal) {
  if (!cards.length) {
    return html`<p class="clue-caption">Nothing pinned yet — set assumptions above and pin them to compare here.</p>`;
  }
  return html`${cards.map((card) => {
    const plan = card.scenario;
    const met = plan.customer_value >= goal;
    const selected = card.id === state.selectedCard;
    return html`
      <div class="clue-lite${selected ? " is-selected" : ""}">
        <button type="button" class="clue-lite-select" data-select="${card.id}"
                aria-pressed="${selected}" aria-label="Select ${card.title}"></button>
        <span class="clue-lite-name">${card.title}</span>
        <span class="clue-lite-note">${card.note}</span>
        <div class="clue-lite-mid">
          <span class="clue-lite-val">${money(plan.customer_value)}</span>
          <span class="clue-goal ${met ? "met" : "missed"}">${met ? "✓ meets goal" : "below goal"}</span>
        </div>
        <div class="clue-lite-sub">${percent(plan.conversion_rate)} ·
          ${decimal(plan.orders_per_purchasing_customer)} · ${money(plan.average_order_value)}</div>
        <button type="button" class="clue-lite-remove" data-remove="${card.id}"
                data-tooltip="Remove ${card.title}" aria-label="Remove ${card.title}">✕</button>
      </div>`;
  })}`;
}

function resultsHtml(b, chosen) {
  if (!chosen) {
    return html`
      <h6>Simulation Results</h6>
      <div class="clue-hint">Select a scenario on the left to see what it implies and how
        the change propagates through the metric.</div>`;
  }
  const plan = chosen.scenario;
  const blocks = [
    ["Scenario assumptions", assumptionLines(b, plan)],
    ["Implied Data Changes", consequenceLines(b, plan)],
    ["Scenario result", resultLines(b, plan)],
  ];
  return html`
    <h6>Simulation Results — ${chosen.title}</h6>
    <div class="clue-result-blocks">
      ${blocks.map(
        ([title, lines]) => html`
          <div class="clue-result-block">
            <div class="clue-result-title">${title}</div>
            <div class="clue-detail-box"><ul>${lines.map((line) => html`<li>${line}</li>`)}</ul></div>
          </div>`
      )}
    </div>
    ${raw(provenanceLegendHtml())}
    <div id="simulation-graph"></div>`;
}

function renderComparison() {
  const b = state.baseline;
  const goal = goalValue(b, state.sim.uplift);
  const cards = comparisonCards();
  const chosen = cards.find((card) => card.id === state.selectedCard) ?? null;

  document.getElementById("scenario-caption").textContent =
    `${count(b.futureAcquiredUsers)} users acquired ${b.futurePeriodLabel} · goal ${money(goal)}`;
  document.getElementById("scenario-list").innerHTML = scenarioListHtml(b, cards, goal);
  document.getElementById("results").innerHTML = resultsHtml(b, chosen);
  if (chosen) {
    renderSimulationGraph(
      document.getElementById("simulation-graph"),
      simulationDeltas(b, chosen.scenario)
    );
  }
}

function renderStrip() {
  document.getElementById("scenario-strip").innerHTML = stripHtml(state.baseline);
}

function renderSimulatorView() {
  initSimulator();
  const b = state.baseline;
  const bounds = sliderBounds(b);

  app.innerHTML = html`
    ${topBar("Back to Main View", "main")}
    ${checksHtml(b)}
    <div class="clue-controls-heading">
      <b>Metric profile assumptions for the next acquisition cohort</b><br>
      <span>Assume users acquired in ${b.futurePeriodLabel} look roughly like this over their
        first ${b.windowDays} days. Below, that profile is translated into a concrete pathway
        you can pin and compare.</span>
    </div>
    <section class="clue-card-panel clue-sim-controls">
      <div class="clue-controls-row">
        ${goalHtml(b)}
        ${sliderHtml("conversion", `${b.windowLabel} Purchase Conversion Rate`,
          bounds.conversion, observedCaption(b, "conversion_rate", percent))}
        ${sliderHtml("orders", "Orders per Purchasing Customer",
          bounds.orders, observedCaption(b, "orders_per_purchasing_customer", decimal))}
        ${sliderHtml("orderValue", "Average Order Value ($)",
          bounds.orderValue, observedCaption(b, "average_order_value", money))}
      </div>
      <div class="clue-strip" id="scenario-strip"></div>
    </section>
    <section class="clue-card-panel clue-sim-split">
      <div class="clue-scenario-col">
        <h6>Scenarios</h6>
        <p class="clue-caption" id="scenario-caption"></p>
        <div id="scenario-list"></div>
      </div>
      <div class="clue-results-col" id="results"></div>
    </section>`;

  wireViewSwitch();
  renderStrip();
  renderComparison();
  wireSimulator();
}

function setUplift(value) {
  const clamped = Math.min(UPLIFT_MAX, Math.max(UPLIFT_MIN, Math.round(Number(value) || 0)));
  state.sim.uplift = clamped;
  document.getElementById("uplift").value = clamped;
  const b = state.baseline;
  document.getElementById("goal-line").innerHTML = html`Historical Baseline:
    <b>${money(b.customer_value)}</b> per acquired user&nbsp;&nbsp;·&nbsp;&nbsp;Goal:
    <b>${money(goalValue(b, clamped))}</b>`;
  renderStrip();
  renderComparison();
}

function wireSimulator() {
  app.querySelectorAll("input[type=range]").forEach((input) => {
    input.addEventListener("input", () => {
      const key = input.dataset.key;
      state.sim[key] = Number(input.value);
      input.style.setProperty(
        "--fill", `${fillPercent(state.sim[key], Number(input.min), Number(input.max))}%`
      );
      document.getElementById(`value-${key}`).textContent = SLIDER_DISPLAY[key](state.sim[key]);
      renderStrip();
    });
  });

  app.querySelectorAll("[data-step]").forEach((button) =>
    button.addEventListener("click", () =>
      setUplift(state.sim.uplift + Number(button.dataset.step) * UPLIFT_STEP)
    )
  );
  document.getElementById("uplift").addEventListener("change", (event) => setUplift(event.target.value));

  // Pin: snapshot the current assumptions; sliders stay put (pin_scenario).
  document.getElementById("scenario-strip").addEventListener("click", (event) => {
    if (!event.target.closest("#pin") || !canPin()) return;
    state.pinned.push({ name: nextScenarioName(), scenario: currentScenario() });
    renderStrip();
    renderComparison();
  });

  // Row click toggles selection; ✕ removes the card (_toggle_card, _remove_card).
  document.querySelector(".clue-sim-split").addEventListener("click", (event) => {
    const remove = event.target.closest("[data-remove]");
    if (remove) {
      const id = remove.dataset.remove;
      if (id === REFERENCE_CARD_ID) state.showReferenceCard = false;
      else state.pinned = state.pinned.filter((p) => p.name !== id);
      if (state.selectedCard === id) state.selectedCard = CURRENT_CARD_ID;
      renderStrip();
      renderComparison();
      return;
    }
    const select = event.target.closest("[data-select]");
    if (select) {
      const id = select.dataset.select;
      state.selectedCard = state.selectedCard === id ? CURRENT_CARD_ID : id;
      renderComparison();
    }
  });
}

// == Page · main.py: hash #simulator switches view

function render() {
  if (location.hash === "#simulator") renderSimulatorView();
  else renderMainView();
  window.scrollTo(0, 0);
}

async function main() {
  installTooltip();
  const [start, end] = referencePeriod();
  try {
    const data = await loadCohorts();
    state.baseline = computeBaseline(data.months, start, end);
  } catch (error) {
    if (!(error instanceof DataMissingError)) throw error;
    state.baseline = fallbackBaseline();
  }
  window.addEventListener("hashchange", render);
  render();
}

main();
