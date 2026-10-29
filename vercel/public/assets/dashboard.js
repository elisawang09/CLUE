// Customer Value Dashboard. Port of baseline_dashboard/app.py + components/; all numbers derive from data/cohorts.json.

import {
  CLUE_PATH,
  DEFAULT_END,
  DEFAULT_START,
  WINDOW_DAYS,
  WINDOW_LABEL,
  count,
  decimal,
  html,
  loadCohorts,
  loadMonthRows,
  money,
  monthLabel,
  ordinal,
  percent,
  periodLabel,
  raw,
  renderFatal,
  safeDivide,
} from "./common.js";

// == Study condition · study/session.py: ?s= token picks the condition; unknown or missing = baseline. Dev tokens only.

const TOKEN_PARAM = "s";
const DEV_TOKENS = { dev: true, "dev-baseline": false };

function resolveSession() {
  const token = new URLSearchParams(location.search).get(TOKEN_PARAM);
  return { token, clueEnabled: Boolean(token && DEV_TOKENS[token]) };
}

// == Metrics · metrics/compute.py

function derive(row) {
  const conversion_rate = safeDivide(row.purchasing_customers, row.acquired_users);
  const orders_per_purchasing_customer = safeDivide(row.total_orders, row.purchasing_customers);
  const average_order_value = safeDivide(row.total_gross_order_value, row.total_orders);
  return {
    ...row,
    label: monthLabel(row.month),
    conversion_rate,
    orders_per_purchasing_customer,
    average_order_value,
    customer_value: conversion_rate * orders_per_purchasing_customer * average_order_value,
  };
}

const EMPTY_MONTH = {
  acquired_users: 0,
  purchasing_customers: 0,
  total_orders: 0,
  total_gross_order_value: 0,
  conversion_rate: NaN,
  orders_per_purchasing_customer: NaN,
  average_order_value: NaN,
  customer_value: NaN,
};

// compute(): cards use the latest month in range; charts use every month in range.
function compute(table, start, end) {
  const inRange = table.filter(
    (row) => ordinal(row.month) >= ordinal(start) && ordinal(row.month) <= ordinal(end)
  );
  const cohort = { start, end, label: periodLabel(start, end) };

  if (!inRange.length) {
    return {
      cohort,
      byMonth: [],
      latest: { ...EMPTY_MONTH, month: end, label: monthLabel(end) },
      previous: null,
    };
  }

  const latest = inRange[inRange.length - 1];
  // Previous month comes from the whole dataset, not just the selection.
  const position = table.indexOf(latest);
  const previous = position > 0 ? table[position - 1] : null;
  return { cohort, byMonth: inRange, latest, previous };
}

function delta(metrics, attribute) {
  if (!metrics.previous) return null;
  const current = metrics.latest[attribute];
  const earlier = metrics.previous[attribute];
  if (Number.isNaN(current) || Number.isNaN(earlier)) return null;
  return current - earlier;
}

function deltaRatio(metrics, attribute) {
  const change = delta(metrics, attribute);
  if (change === null) return null;
  const earlier = metrics.previous[attribute];
  return earlier ? change / Math.abs(earlier) : null;
}

// == Consistency checks · metrics/checks.py · run_checks()

const TOLERANCE = 1e-3;

function close(a, b) {
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  return Math.abs(a - b) <= TOLERANCE + TOLERANCE * Math.abs(b);
}

function runChecks(metrics) {
  const m = metrics.latest;
  const headline = m.customer_value;
  const product = m.conversion_rate * m.orders_per_purchasing_customer * m.average_order_value;
  const simplified = safeDivide(m.total_gross_order_value, m.acquired_users);

  const results = [
    {
      name: "headline == conversion x orders x AOV",
      passed: close(headline, product),
      detail: `${headline.toFixed(6)} vs ${product.toFixed(6)}`,
    },
    {
      name: "headline == total gross value / acquired users",
      passed: close(headline, simplified),
      detail: `${headline.toFixed(6)} vs ${simplified.toFixed(6)}`,
    },
  ];

  if (metrics.byMonth.length) {
    const row = metrics.byMonth[metrics.byMonth.length - 1];
    results.push({
      name: "cards report the latest month in the period",
      passed: close(row.customer_value, headline) && row.acquired_users === m.acquired_users,
      detail: `${row.month} ${row.customer_value.toFixed(6)} vs ${m.month} ${headline.toFixed(6)}`,
    });

    const worst = (values) => Math.max(0, ...values.filter((v) => !Number.isNaN(v)));
    const productGap = worst(
      metrics.byMonth.map((r) =>
        Math.abs(
          r.customer_value -
            r.conversion_rate * r.orders_per_purchasing_customer * r.average_order_value
        )
      )
    );
    const simplifiedGap = worst(
      metrics.byMonth.map((r) =>
        Math.abs(r.customer_value - safeDivide(r.total_gross_order_value, r.acquired_users))
      )
    );
    const months = metrics.byMonth.length;
    results.push(
      {
        name: "every charted month == conversion x orders x AOV",
        passed: productGap <= TOLERANCE,
        detail: `largest disagreement ${productGap.toFixed(9)} across ${months} month(s)`,
      },
      {
        name: "every charted month == gross value / acquired users",
        passed: simplifiedGap <= TOLERANCE,
        detail: `largest disagreement ${simplifiedGap.toFixed(9)} across ${months} month(s)`,
      }
    );
  }
  return results;
}

// == Card metrics · metrics/registry.py · METRICS

const CUSTOMER_GRAIN = "customer";
const ORDER_GRAIN = "order";
const PRIMARY_ID = "customer_value";

const METRICS = {
  customer_value: {
    name: () => `${WINDOW_LABEL} Customer Value`,
    description: (m) =>
      `Average value generated per acquired user during their first ${WINDOW_DAYS} ` +
      `days after acquisition. Every user acquired in ${m.latest.label} counts ` +
      `toward the average, including those who never placed an order.`,
    fmt: money,
    grain: CUSTOMER_GRAIN,
    unit: "per acquired user",
    clueMetric: `${WINDOW_LABEL} Customer Value`,
  },
  conversion_rate: {
    name: () => `${WINDOW_LABEL} Purchase Conversion Rate`,
    description: () =>
      `Percentage of acquired users who place at least one order during their ` +
      `first ${WINDOW_DAYS} days after acquisition. Users who first order later ` +
      `than that are not counted.`,
    fmt: percent,
    grain: CUSTOMER_GRAIN,
  },
  orders_per_purchasing_customer: {
    name: () => "Orders per Purchasing Customer",
    description: () =>
      `Average number of orders placed by a customer who ordered at least once ` +
      `in their first ${WINDOW_DAYS} days. Users who never ordered in that window ` +
      `are excluded from this average.`,
    fmt: decimal,
    grain: CUSTOMER_GRAIN,
  },
  average_order_value: {
    name: () => "Average Order Value",
    description: () =>
      "Average gross value of a single qualifying order -- what the order was " +
      "worth after the cost of the items in it.",
    fmt: money,
    grain: ORDER_GRAIN,
  },
  acquired_users: {
    name: () => "Acquired Users",
    description: (m) =>
      `Number of users whose account was created in ${m.latest.label}, whether or ` +
      `not they went on to order. This is the most recent acquisition month in ` +
      `the reference period.`,
    fmt: count,
    grain: CUSTOMER_GRAIN,
  },
};

const CARD_IDS = Object.keys(METRICS);

function formattedValue(metricId, metrics) {
  const value = metrics.latest[metricId];
  return Number.isNaN(value) ? "—" : METRICS[metricId].fmt(value);
}

// == Page state (st.session_state in app.py)

const state = {
  table: [],
  months: [],
  start: DEFAULT_START,
  end: DEFAULT_END,
  metrics: null,
  session: resolveSession(),
  selectedMetric: null,     // which KPI card is outlined
  pickedLeft: null,         // acquisition month clicked on each chart
  pickedRight: null,
};

const selectedMonth = () => state.pickedLeft ?? state.pickedRight;

// == Filter · components/filters.py · render_filters()

function renderFilters() {
  const options = state.months
    .map((month) => html`<option value="${month}">${monthLabel(month)}</option>`)
    .join("");
  const from = document.getElementById("filter-start");
  const to = document.getElementById("filter-end");
  from.innerHTML = options;
  to.innerHTML = options;

  const has = (month) => state.months.includes(month);
  state.start = has(DEFAULT_START) ? DEFAULT_START : state.months[0];
  state.end = has(DEFAULT_END) ? DEFAULT_END : state.months[state.months.length - 1];
  from.value = state.start;
  to.value = state.end;

  const onChange = () => {
    state.start = from.value;
    state.end = to.value;
    state.pickedLeft = state.pickedRight = null;
    update();
  };
  from.addEventListener("change", onChange);
  to.addEventListener("change", onChange);
}

// Returns [start, end]; swaps a reversed range and shows a warning.
function cohortRange() {
  const warning = document.getElementById("filter-warning");
  if (ordinal(state.start) > ordinal(state.end)) {
    warning.hidden = false;
    warning.textContent =
      `Acquisition period starts after it ends (${monthLabel(state.start)} → ` +
      `${monthLabel(state.end)}); showing ${monthLabel(state.end)} → ` +
      `${monthLabel(state.start)} instead.`;
    return [state.end, state.start];
  }
  warning.hidden = true;
  return [state.start, state.end];
}

// == KPI cards · components/kpi_cards.py

function formatDelta(metricId, change) {
  // Rate changes are shown in percentage points.
  if (METRICS[metricId].fmt === percent) return `${(Math.abs(change) * 100).toFixed(1)} pts`;
  return METRICS[metricId].fmt(Math.abs(change));
}

function deltaHtml(metricId, metrics) {
  const change = delta(metrics, metricId);
  // No previous month: keep the line's height but show no delta.
  if (change === null) return html`<div class="bd-kpi-delta">&nbsp;</div>`;

  const ratio = deltaRatio(metrics, metricId);
  const [direction, arrow] =
    change > 0 ? ["is-up", "▲"] : change < 0 ? ["is-down", "▼"] : ["is-flat", "—"];
  const relative = ratio !== null ? ` (${(Math.abs(ratio) * 100).toFixed(1)}%)` : "";
  return html`
    <div class="bd-kpi-delta ${direction}">
      ${arrow} ${formatDelta(metricId, change)}${relative}
      <span class="bd-delta-context">vs ${metrics.previous.label}</span>
    </div>`;
}

function clueUrl(metrics) {
  const params = new URLSearchParams({
    metric: METRICS[PRIMARY_ID].clueMetric,
    start: metrics.cohort.start,
    end: metrics.cohort.end,
  });
  if (state.session.token) params.set(TOKEN_PARAM, state.session.token);
  return `${CLUE_PATH}?${params}`;
}

function menuHtml(metricId, metrics) {
  // "Open in CLUE": CLUE condition only, mapped metrics only (clue.py · clue_url_for).
  const clue =
    state.session.clueEnabled && METRICS[metricId].clueMetric
      ? html`<a class="bd-menu-item" href="${clueUrl(metrics)}" target="_blank"
               rel="noopener">Open in CLUE ↗</a>`
      : "";
  return html`
    <div class="bd-menu">
      <button class="bd-menu-trigger" type="button" aria-haspopup="true"
              aria-expanded="false" aria-label="More options">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>
        </svg>
      </button>
      <div class="bd-menu-body" hidden>
        <button class="bd-menu-item" type="button" data-action="underlying"
                data-metric="${metricId}">View Underlying Data</button>
        ${clue}
      </div>
    </div>`;
}

function renderCards(metrics) {
  const container = document.getElementById("kpi-cards");
  container.innerHTML = CARD_IDS.map((metricId) => {
    const metric = METRICS[metricId];
    const selected = metricId === state.selectedMetric ? " is-selected" : "";
    return html`
      <section class="card bd-kpi${selected}" data-metric="${metricId}">
        <div class="bd-kpi-head">
          <p class="bd-kpi-label" title="${metric.description(metrics)}">${metric.name()}</p>
          ${menuHtml(metricId, metrics)}
        </div>
        <div class="bd-kpi-month">${metrics.latest.label}</div>
        <div class="bd-kpi-value${metricId === PRIMARY_ID ? " is-primary" : ""}">
          ${formattedValue(metricId, metrics)}
        </div>
        <div class="bd-kpi-unit">${metric.unit ?? raw("&nbsp;")}</div>
        ${deltaHtml(metricId, metrics)}
      </section>`;
  }).join("");
}

function closeMenus(except = null) {
  document.querySelectorAll(".bd-menu").forEach((menu) => {
    if (menu === except) return;
    menu.querySelector(".bd-menu-body").hidden = true;
    menu.querySelector(".bd-menu-trigger").setAttribute("aria-expanded", "false");
  });
}

function wireMenus() {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".bd-menu-trigger");
    if (trigger) {
      const menu = trigger.closest(".bd-menu");
      const body = menu.querySelector(".bd-menu-body");
      closeMenus(menu);
      body.hidden = !body.hidden;
      trigger.setAttribute("aria-expanded", String(!body.hidden));
      return;
    }
    const item = event.target.closest("[data-action='underlying']");
    if (item) {
      closeMenus();
      state.selectedMetric = item.dataset.metric;
      document.querySelectorAll(".bd-kpi").forEach((card) => {
        card.classList.toggle("is-selected", card.dataset.metric === state.selectedMetric);
      });
      openUnderlying(item.dataset.metric);
      return;
    }
    if (!event.target.closest(".bd-menu-body")) closeMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });
}

// == Charts · components/charts.py

const SERIES = "#2a78d6";
const SERIES_MUTED = "#a9c8ee";
const BORDER = "#E3E8EF";
const GRID = "#EEF1F6";
const TEXT_SECONDARY = "#5B6472";
const TEXT_MUTED = "#8A93A3";
const FONT =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

const CHART_HEIGHT = 300;
// Above this many months, per-bar value labels are dropped.
const MAX_LABELLED_MONTHS = 12;

function chartSpec(metrics, width, field, axisTitle, axisFormat, labelFormat, tooltipTitle) {
  const values = metrics.byMonth.map((row) => ({
    month_label: row.label,
    is_latest: row.month === metrics.latest.month,
    customer_value: row.customer_value,
    conversion_rate: row.conversion_rate,
    acquired_users: row.acquired_users,
    purchasing_customers: row.purchasing_customers,
  }));

  const x = {
    field: "month_label",
    type: "nominal",
    // Oldest to newest, as an explicit list so both layers share one sort.
    sort: values.map((value) => value.month_label),
    title: "User Acquisition Month",
    // Angle the labels when each column gets less than 72px.
    axis: { labelAngle: width / Math.max(values.length, 1) >= 72 ? 0 : -45, grid: false },
    scale: { paddingInner: 0.25, paddingOuter: 0.15 },
  };
  const y = {
    field,
    type: "quantitative",
    title: axisTitle,
    axis: { format: axisFormat, tickCount: 6 },
    scale: { nice: true, zero: true },
  };

  const layers = [
    {
      params: [{ name: "pick", select: { type: "point", fields: ["month_label"], on: "click" } }],
      mark: { type: "bar", cornerRadiusTopLeft: 4, cornerRadiusTopRight: 4, cursor: "pointer" },
      encoding: {
        x,
        y,
        // Latest month in the accent colour; a click mutes the unselected bars.
        color: {
          condition: {
            param: "pick",
            empty: true,
            field: "is_latest",
            type: "nominal",
            scale: { domain: [false, true], range: [SERIES_MUTED, SERIES] },
            legend: null,
          },
          value: SERIES_MUTED,
        },
        tooltip: [
          { field: "month_label", type: "nominal", title: "User Acquisition Month" },
          { field, type: "quantitative", title: tooltipTitle, format: labelFormat },
          { field: "acquired_users", type: "quantitative", title: "Acquired users", format: "," },
          {
            field: "purchasing_customers",
            type: "quantitative",
            title: "Purchasing customers",
            format: ",",
          },
        ],
      },
    },
  ];
  if (values.length <= MAX_LABELLED_MONTHS) {
    layers.push({
      mark: { type: "text", dy: -9, fontSize: 11, color: TEXT_SECONDARY },
      encoding: { x, y, text: { field, type: "quantitative", format: labelFormat } },
    });
  }

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    width: "container",
    height: CHART_HEIGHT,
    autosize: { type: "fit-x", contains: "padding" },
    data: { values },
    layer: layers,
    config: {
      view: { stroke: null },
      font: FONT,
      axis: {
        labelFont: FONT,
        titleFont: FONT,
        labelColor: TEXT_SECONDARY,
        titleColor: TEXT_MUTED,
        titleFontSize: 11,
        labelFontSize: 11,
        titlePadding: 12,
        domainColor: BORDER,
        tickColor: BORDER,
        gridColor: GRID,
      },
    },
  };
}

function pickedMonth(value) {
  // Selection signal is {month_label: [label]}, or {} when cleared.
  const labels = value?.month_label;
  return Array.isArray(labels) && labels.length ? String(labels[0]) : null;
}

const CHARTS = [
  {
    elementId: "chart-customer-value",
    side: "pickedLeft",
    args: ["customer_value", "Value per acquired user", "$,.0f", "$,.2f",
      `${WINDOW_LABEL} Customer Value`],
  },
  {
    elementId: "chart-conversion",
    side: "pickedRight",
    args: ["conversion_rate", "Share of acquired users", ".0%", ".1%",
      `${WINDOW_LABEL} Conversion Rate`],
  },
];

async function renderChart({ elementId, side, args }, metrics) {
  const element = document.getElementById(elementId);
  if (!metrics.byMonth.length) {
    element.innerHTML = html`<div class="bd-chart-empty">No users were acquired in this reference period.</div>`;
    return;
  }
  const spec = chartSpec(metrics, element.clientWidth, ...args);
  element.dataset.labelAngle = spec.layer[0].encoding.x.axis.labelAngle;
  const result = await window.vegaEmbed(element, spec, { actions: false, renderer: "svg" });
  result.view.addSignalListener("pick", (_, value) => {
    state[side] = pickedMonth(value);
  });
}

function renderCharts(metrics) {
  CHARTS.forEach((chart) => renderChart(chart, metrics));
}

// Redraws a chart only when its label angle changes; Vega handles width itself.
function wireResize() {
  let timer;
  window.addEventListener("resize", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const metrics = state.metrics;
      if (!metrics?.byMonth.length) return;
      CHARTS.forEach((chart) => {
        const element = document.getElementById(chart.elementId);
        const angle = chartSpec(metrics, element.clientWidth, ...chart.args)
          .layer[0].encoding.x.axis.labelAngle;
        if (String(angle) !== element.dataset.labelAngle) {
          state[chart.side] = null;
          renderChart(chart, metrics);
        }
      });
    }, 150);
  });
}

// == View Underlying Data · components/underlying_data.py: rows for the month the cards report.

const DEFAULT_ROWS = 200;
const CUSTOMER_GRAIN_LABEL = "One row per acquired user";
const ORDER_GRAIN_LABEL = "One row per order";
const MONEY_COLUMNS = new Set([
  `gross_value_${WINDOW_DAYS}d`, "revenue", "cost", "gross_value",
  "Total Gross Order Value", `${WINDOW_LABEL} Customer Value`,
]);

function cell(column, value) {
  if (value === null || value === undefined) return "";
  // Money columns always show cents, like Streamlit's "$%.2f".
  if (MONEY_COLUMNS.has(column)) {
    return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (column.endsWith("Conversion Rate")) return percent(value);
  if (typeof value === "number" && !column.endsWith("_id")) return count(value);
  return String(value);
}

function tableHtml(columns, rows) {
  const numeric = columns.map((_, i) => rows.some((row) => typeof row[i] === "number"));
  return html`
    <table class="bd-table">
      <thead><tr>${columns.map((c, i) => html`<th class="${numeric[i] ? "num" : ""}">${c}</th>`)}</tr></thead>
      <tbody>
        ${rows.map(
          (row) => html`<tr>${row.map(
            (value, i) => html`<td class="${numeric[i] ? "num" : ""}">${cell(columns[i], value)}</td>`
          )}</tr>`
        )}
      </tbody>
    </table>`;
}

function summaryHtml(metrics) {
  const m = metrics.latest;
  const columns = [
    "Acquisition Month", "Acquired Users", "Purchasing Customers", "Total Orders",
    "Total Gross Order Value", `${WINDOW_LABEL} Customer Value`,
  ];
  const row = [
    m.label, m.acquired_users, m.purchasing_customers, m.total_orders,
    m.total_gross_order_value, m.customer_value,
  ];

  let detail = "";
  const picked = selectedMonth();
  const month = picked && metrics.byMonth.find((r) => r.label === picked);
  if (month) {
    detail = html`
      <p class="bd-dialog-subhead">Selected month — ${picked}</p>
      ${tableHtml(
        ["Acquisition Month", "Acquired Users", "Purchasing Customers",
          `${WINDOW_LABEL} Purchase Conversion Rate`, `${WINDOW_LABEL} Customer Value`],
        [[picked, month.acquired_users, month.purchasing_customers,
          month.conversion_rate, month.customer_value]]
      )}`;
  }
  return html`
    <p class="bd-caption">The selected marks at the level the dashboard aggregates them.</p>
    ${tableHtml(columns, [row])}
    ${detail}`;
}

async function renderRows(metrics, grain, panel) {
  const shown = panel.querySelector(".bd-rows-table");
  const footer = panel.querySelector(".bd-rows-footer");
  const caption = panel.querySelector(".bd-rows-caption");
  const input = panel.querySelector("input[type=number]");

  caption.textContent =
    grain === CUSTOMER_GRAIN_LABEL
      ? `Every user acquired ${metrics.latest.label}, with their orders and gross value ` +
        `over their first ${WINDOW_DAYS} days. Users who never ordered appear with zeros.`
      : `Every order placed by these users within their first ${WINDOW_DAYS} days. ` +
        `gross_value is revenue − cost, and days_since_acquisition counts from each ` +
        `user's own signup day.`;

  if (!metrics.byMonth.length) {
    shown.innerHTML = "";
    footer.textContent = "Showing 0 of 0 rows.";
    return;
  }

  shown.innerHTML = html`<div class="bd-loading">Loading rows…</div>`;
  let data;
  try {
    data = await loadMonthRows(metrics.latest.month);
  } catch (error) {
    shown.innerHTML = html`<div class="bd-error">${error.message}</div>`;
    return;
  }
  const frame = grain === CUSTOMER_GRAIN_LABEL ? data.customers : data.orders;
  const total = frame.rows.length;

  input.max = String(Math.max(total, 10));
  if (!input.dataset.touched) input.value = String(Math.min(DEFAULT_ROWS, Math.max(total, 10)));
  const limit = Math.max(10, Math.min(Number(input.value) || DEFAULT_ROWS, Math.max(total, 10)));

  shown.innerHTML = tableHtml(frame.columns, frame.rows.slice(0, limit));
  footer.textContent = `Showing ${count(Math.min(limit, total))} of ${count(total)} rows.`;
}

function openUnderlying(metricId) {
  const metrics = state.metrics;
  const dialog = document.getElementById("underlying-dialog");
  const picked = selectedMonth();
  const scope = picked ? ` · ${picked} selected on a chart` : "";
  const defaultGrain =
    METRICS[metricId].grain === ORDER_GRAIN ? ORDER_GRAIN_LABEL : CUSTOMER_GRAIN_LABEL;

  dialog.querySelector(".bd-dialog-body").innerHTML = html`
    <h3>${METRICS[metricId].name()}</h3>
    <p class="bd-caption">Users acquired ${metrics.latest.label} · first ${WINDOW_DAYS} days${scope}</p>
    <div class="bd-tabs" role="tablist">
      <button type="button" role="tab" class="is-active" data-tab="summary">Summary</button>
      <button type="button" role="tab" data-tab="rows">Underlying rows</button>
    </div>
    <div class="bd-tab-panel" data-panel="summary">${summaryHtml(metrics)}</div>
    <div class="bd-tab-panel" data-panel="rows" hidden>
      <fieldset class="bd-grain">
        <legend>Level of detail</legend>
        ${[CUSTOMER_GRAIN_LABEL, ORDER_GRAIN_LABEL].map(
          (label) => html`<label><input type="radio" name="grain" value="${label}"
            ${label === defaultGrain ? raw("checked") : ""}> ${label}</label>`
        )}
      </fieldset>
      <p class="bd-caption bd-rows-caption"></p>
      <label class="bd-row-count">Rows to display
        <input type="number" min="10" step="50" value="${DEFAULT_ROWS}">
      </label>
      <div class="bd-rows-table"></div>
      <p class="bd-caption bd-rows-footer"></p>
    </div>`;

  const body = dialog.querySelector(".bd-dialog-body");
  const rowsPanel = body.querySelector("[data-panel=rows]");
  const grain = () => body.querySelector("input[name=grain]:checked").value;

  body.querySelectorAll("[role=tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      body.querySelectorAll("[role=tab]").forEach((t) => t.classList.toggle("is-active", t === tab));
      body.querySelectorAll(".bd-tab-panel").forEach((panel) => {
        panel.hidden = panel.dataset.panel !== tab.dataset.tab;
      });
    });
  });
  body.querySelectorAll("input[name=grain]").forEach((radio) =>
    radio.addEventListener("change", () => renderRows(metrics, grain(), rowsPanel))
  );
  const rowCount = body.querySelector("input[type=number]");
  rowCount.addEventListener("change", () => {
    rowCount.dataset.touched = "1";
    renderRows(metrics, grain(), rowsPanel);
  });

  renderRows(metrics, defaultGrain, rowsPanel);
  dialog.showModal();
}

function wireDialog() {
  const dialog = document.getElementById("underlying-dialog");
  dialog.querySelectorAll("[data-close]").forEach((button) =>
    button.addEventListener("click", () => dialog.close())
  );
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

// == Page · app.py · main()

function reportChecks(metrics) {
  const banner = document.getElementById("checks");
  const failed = runChecks(metrics).filter((check) => !check.passed);
  banner.hidden = !failed.length;
  banner.innerHTML = failed.length
    ? html`<strong>Metric consistency check failed — these numbers should not be used:</strong>
        <ul>${failed.map((c) => html`<li><b>${c.name}</b> — ${c.detail}</li>`)}</ul>`
    : "";
}

function update() {
  const [start, end] = cohortRange();
  const metrics = compute(state.table, start, end);
  state.metrics = metrics;

  reportChecks(metrics);
  renderCards(metrics);
  renderCharts(metrics);

  document.getElementById("footer-caption").textContent =
    `Customer Analytics Model · cards show ${count(metrics.latest.acquired_users)} users ` +
    `acquired ${metrics.latest.label}, the most recent month in ${metrics.cohort.label}; ` +
    `each is observed for their own first ${WINDOW_DAYS} days.`;
}

async function main() {
  try {
    const data = await loadCohorts();
    state.table = data.months.map(derive);
    state.months = state.table.map((row) => row.month);
  } catch (error) {
    renderFatal(document.querySelector("main"), error);
    return;
  }

  document.getElementById("filter-caption").textContent =
    `Users are included by acquisition date, then observed for their own first ` +
    `${WINDOW_DAYS} days, so everyone gets an equal-length window. Cards show the ` +
    `most recent acquisition month in the range; charts show every month in it.`;

  renderFilters();
  wireMenus();
  wireDialog();
  wireResize();
  update();
}

main();
