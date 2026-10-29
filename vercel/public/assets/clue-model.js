// CLUE's numbers and graph definitions. Port of demo/data/metrics.py, scenario.py and graph_data.py.

import {
  DEFAULT_END,
  DEFAULT_START,
  WINDOW_DAYS,
  WINDOW_LABEL,
  addMonths,
  count,
  decimal,
  monthLabel,
  money,
  ordinal,
  parseMonth,
  percent,
  periodLabel,
  safeDivide,
  wholeMoney,
} from "./common.js";

export const PRIMARY_METRIC = `${WINDOW_LABEL} Customer Value`;

// == Reference period · metrics.py · reference_period(): ?start/?end, else Jan-Jun 2024

export function referencePeriod(params = new URLSearchParams(location.search)) {
  const start = parseMonth(params.get("start"));
  const end = parseMonth(params.get("end"));
  if (!start || !end) return [DEFAULT_START, DEFAULT_END];
  return ordinal(start) > ordinal(end) ? [end, start] : [start, end];
}

// Months the simulator plans ahead of the explained cohort.
const FUTURE_MONTHS = 3;

function futureWindow(cohort) {
  return [addMonths(cohort, 1), addMonths(cohort, FUTURE_MONTHS)];
}

// Future cohort size: same 3 months a year earlier, else 3 × this cohort (_future_acquired_users).
function futureAcquiredUsers(acquiredByMonth, cohort) {
  const [start] = futureWindow(cohort);
  const months = [0, 1, 2].map((i) => addMonths(start, i - 12));
  const available = months.filter((month) => acquiredByMonth.has(month));
  const total = available.reduce((sum, month) => sum + acquiredByMonth.get(month), 0);
  if (available.length && total > 0) return total;
  return (acquiredByMonth.get(cohort) ?? 0) * FUTURE_MONTHS;
}

// == Baseline · metrics.py · compute_baseline()

function fromTotals(totals, extra) {
  const conversion_rate = safeDivide(totals.purchasing_customers, totals.acquired_users);
  const orders_per_purchasing_customer = safeDivide(totals.total_orders, totals.purchasing_customers);
  const average_order_value = safeDivide(totals.total_gross_order_value, totals.total_orders);
  const baseline = {
    acquired_users: totals.acquired_users,
    purchasing_customers: totals.purchasing_customers,
    total_orders: totals.total_orders,
    total_gross_order_value: totals.total_gross_order_value,
    conversion_rate,
    orders_per_purchasing_customer,
    average_order_value,
    customer_value: conversion_rate * orders_per_purchasing_customer * average_order_value,
    windowDays: WINDOW_DAYS,
    windowLabel: WINDOW_LABEL,
    isFallback: false,
    ...extra,
  };
  baseline.focus = baseline.byMonth.find((point) => point.is_focus) ?? null;
  return baseline;
}

// Baseline for the latest month in the period, plus every month for the chart.
export function computeBaseline(table, start, end) {
  const acquiredByMonth = new Map(table.map((row) => [row.month, row.acquired_users]));
  const inPeriod = table.filter(
    (row) => ordinal(row.month) >= ordinal(start) && ordinal(row.month) <= ordinal(end)
  );

  if (!inPeriod.length) {
    const [futureStart, futureEnd] = futureWindow(end);
    return fromTotals(
      { acquired_users: 0, purchasing_customers: 0, total_orders: 0, total_gross_order_value: 0 },
      {
        byMonth: [],
        futureAcquiredUsers: 0,
        cohortLabel: monthLabel(end),
        periodLabel: periodLabel(start, end),
        futurePeriodLabel: periodLabel(futureStart, futureEnd),
      }
    );
  }

  // Headline = latest month in the period, same rule as the dashboard cards.
  const focus = inPeriod[inPeriod.length - 1];
  const byMonth = inPeriod.map((row) => ({
    month: row.month,
    month_label: monthLabel(row.month),
    acquired_users: row.acquired_users,
    purchasing_customers: row.purchasing_customers,
    customer_value: safeDivide(row.total_gross_order_value, row.acquired_users),
    conversion_rate: safeDivide(row.purchasing_customers, row.acquired_users),
    orders_per_purchasing_customer: safeDivide(row.total_orders, row.purchasing_customers),
    average_order_value: safeDivide(row.total_gross_order_value, row.total_orders),
    is_focus: row === focus,
  }));
  const [futureStart, futureEnd] = futureWindow(focus.month);

  return fromTotals(focus, {
    byMonth,
    futureAcquiredUsers: futureAcquiredUsers(acquiredByMonth, focus.month),
    cohortLabel: monthLabel(focus.month),
    periodLabel: periodLabel(start, end),
    futurePeriodLabel: periodLabel(futureStart, futureEnd),
  });
}

// Reference example used when data/ is missing (_fallback_baseline).
export function fallbackBaseline() {
  const labels = ["Jan 2024", "Feb 2024", "Mar 2024", "Apr 2024", "May 2024", "Jun 2024"];
  const values = [88.0, 92.0, 97.0, 101.0, 99.0, 104.0];
  const rates = [0.36, 0.38, 0.39, 0.4, 0.39, 0.4];
  const orders = [4.8, 5.0, 5.1, 5.2, 5.0, 5.3];
  const orderValues = [9.17, 9.68, 9.76, 10.1, 10.15, 10.4];
  const counts = {
    acquired_users: 500,
    purchasing_customers: 200,
    total_orders: 1000,
    total_gross_order_value: 52000,
  };
  const byMonth = labels.map((label, i) => ({
    month_label: label,
    acquired_users: counts.acquired_users,
    purchasing_customers: counts.purchasing_customers,
    customer_value: values[i],
    conversion_rate: rates[i],
    orders_per_purchasing_customer: orders[i],
    average_order_value: orderValues[i],
    is_focus: i === labels.length - 1,
  }));
  return {
    ...fromTotals(counts, {
      byMonth,
      futureAcquiredUsers: counts.acquired_users * FUTURE_MONTHS,
      cohortLabel: labels[labels.length - 1],
      periodLabel: periodLabel(DEFAULT_START, DEFAULT_END),
      futurePeriodLabel: "Jul-Sep 2024",
    }),
    isFallback: true,
  };
}

// [min, max] of one factor across the period (BaselineMetrics.observed_range).
export function observedRange(baseline, attribute) {
  const values = baseline.byMonth
    .map((point) => point[attribute])
    .filter((value) => !Number.isNaN(value));
  return values.length ? [Math.min(...values), Math.max(...values)] : [NaN, NaN];
}

// == Consistency checks · metrics.py · run_checks()

const TOLERANCE = 1e-3;

function close(a, b) {
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  return Math.abs(a - b) <= TOLERANCE + TOLERANCE * Math.abs(b);
}

export function failedChecks(b) {
  const headline = b.customer_value;
  const product = b.conversion_rate * b.orders_per_purchasing_customer * b.average_order_value;
  const simplified = safeDivide(b.total_gross_order_value, b.acquired_users);
  const focus = b.focus;
  const f6 = (value) => value.toFixed(6);

  const results = [
    [`${WINDOW_LABEL} Customer Value == conversion x orders per customer x AOV`,
      close(headline, product), `${f6(headline)} vs ${f6(product)}`],
    [`${WINDOW_LABEL} Customer Value == total gross order value / acquired users`,
      close(headline, simplified), `${f6(headline)} vs ${f6(simplified)}`],
    ["Purchasing Customers == acquired users x conversion rate",
      close(b.purchasing_customers, b.acquired_users * b.conversion_rate),
      `${b.purchasing_customers} vs ${f6(b.acquired_users * b.conversion_rate)}`],
    ["Total Orders == purchasing customers x orders per customer",
      close(b.total_orders, b.purchasing_customers * b.orders_per_purchasing_customer),
      `${b.total_orders} vs ${f6(b.purchasing_customers * b.orders_per_purchasing_customer)}`],
    ["Total Gross Order Value == total orders x AOV",
      close(b.total_gross_order_value, b.total_orders * b.average_order_value),
      `${f6(b.total_gross_order_value)} vs ${f6(b.total_orders * b.average_order_value)}`],
    // The highlighted bar must be the explained cohort.
    ["highlighted month on the chart == the explained cohort",
      focus !== null &&
        focus.month_label === b.cohortLabel &&
        close(focus.customer_value, headline) &&
        focus.acquired_users === b.acquired_users,
      `${focus ? `${focus.month_label} ${f6(focus.customer_value)}` : "no highlighted month"}` +
        ` vs ${b.cohortLabel} ${f6(headline)}`],
  ];
  return results
    .filter(([, passed]) => !passed)
    .map(([name, , detail]) => ({ name, detail }));
}

// Formatted value per provenance node, for tooltips (node_values).
export function nodeValues(b) {
  return {
    cust_val: money(b.customer_value),
    conv_rate: percent(b.conversion_rate),
    orders_per_cust: decimal(b.orders_per_purchasing_customer),
    avg_order_val: money(b.average_order_value),
    acq_users: count(b.acquired_users),
    purch_cust_1: count(b.purchasing_customers),
    purch_cust_2: count(b.purchasing_customers),
    tot_orders_1: count(b.total_orders),
    tot_orders_2: count(b.total_orders),
    tot_gross_val: wholeMoney(b.total_gross_order_value),
  };
}

// == Scenarios · data/scenario.py: three assumptions; counts and headline are propagated from them.

export const DEFAULT_UPLIFT_PERCENT = 15;

export function scenario(conversion_rate, orders_per_purchasing_customer, average_order_value, acquired_users) {
  const purchasing_customers = acquired_users * conversion_rate;
  const total_orders = purchasing_customers * orders_per_purchasing_customer;
  return {
    conversion_rate,
    orders_per_purchasing_customer,
    average_order_value,
    acquired_users,
    purchasing_customers,
    total_orders,
    total_gross_order_value: total_orders * average_order_value,
    customer_value: conversion_rate * orders_per_purchasing_customer * average_order_value,
  };
}

// Baseline factors applied to the future cohort (from_baseline).
export function fromBaseline(b) {
  return scenario(
    b.conversion_rate, b.orders_per_purchasing_customer, b.average_order_value,
    b.futureAcquiredUsers
  );
}

// Each factor at its best month in the period (from_observed_best).
export function fromObservedBest(b) {
  return scenario(
    observedRange(b, "conversion_rate")[1],
    observedRange(b, "orders_per_purchasing_customer")[1],
    observedRange(b, "average_order_value")[1],
    b.futureAcquiredUsers
  );
}

export function goalValue(b, upliftPercent) {
  return b.customer_value * (1 + upliftPercent / 100);
}

// == Provenance graph · data/graph_data.py · NODES/EDGES. x/y are logical column/row.

export const NODES = [
  {
    id: "cust_val", label: PRIMARY_METRIC, type: "root", x: 0, y: 2,
    description:
      "Average value generated per acquired user during their first 90 days after " +
      "acquisition. Calculated as 90-Day Purchase Conversion Rate × Orders per " +
      "Purchasing Customer × Average Order Value.",
  },
  { id: "op_mul", label: "", type: "operator", symbol: "×", x: 1, y: 2 },
  { id: "op_div1", label: "", type: "operator", symbol: "÷", x: 3, y: 0 },
  { id: "op_div2", label: "", type: "operator", symbol: "÷", x: 3, y: 2 },
  { id: "op_div3", label: "", type: "operator", symbol: "÷", x: 3, y: 4 },
  {
    id: "conv_rate", label: "90-Day Purchase Conversion Rate", type: "ratio", symbol: "%", x: 2, y: 0,
    description:
      "Share of acquired users who place at least one order within their first 90 " +
      "days. Calculated as Purchasing Customers ÷ Acquired Users.",
  },
  {
    id: "orders_per_cust", label: "Orders per Purchasing Customer", type: "metric", symbol: "#", x: 2, y: 2,
    description:
      "Average number of orders placed by a customer who ordered at least once in " +
      "their first 90 days. Users who never ordered are excluded from this average. " +
      "Calculated as Total Orders ÷ Purchasing Customers.",
  },
  {
    id: "avg_order_val", label: "Average Order Value", type: "metric", symbol: "#", x: 2, y: 4,
    description:
      "Average gross value of a single qualifying order. Calculated as Total Gross " +
      "Order Value ÷ Total Orders.",
  },
  {
    id: "purch_cust_1", label: "Purchasing Customers", type: "metric", symbol: "#", x: 4, y: -0.5,
    description:
      "Acquired users with at least one qualifying order during their first 90 days " +
      "after acquisition.",
  },
  {
    id: "acq_users", label: "Acquired Users", type: "metric", symbol: "#", x: 4, y: 0.5,
    description:
      "Users acquired during the reference acquisition period, whether or not they " +
      "went on to order. Non-purchasing users stay in the denominator of the metric.",
  },
  {
    id: "tot_orders_1", label: "Total Orders", type: "metric", symbol: "#", x: 4, y: 1.5,
    description:
      "Orders placed by the acquisition group, counting only orders within each " +
      "user's own first 90 days.",
  },
  {
    id: "purch_cust_2", label: "Purchasing Customers", type: "metric", symbol: "#", x: 4, y: 2.5,
    description:
      "Acquired users with at least one qualifying order during their first 90 days " +
      "after acquisition.",
  },
  {
    id: "tot_gross_val", label: "Total Gross Order Value", type: "metric", symbol: "#", x: 4, y: 3.5,
    description:
      "Gross value of all qualifying orders, summed across every order line, where " +
      "gross_value = revenue − cost.",
  },
  {
    id: "tot_orders_2", label: "Total Orders", type: "metric", symbol: "#", x: 4, y: 4.5,
    description:
      "Orders placed by the acquisition group, counting only orders within each " +
      "user's own first 90 days.",
  },
];

export const EDGES = [
  ["cust_val", "op_mul"],
  ["op_mul", "conv_rate"],
  ["op_mul", "orders_per_cust"],
  ["op_mul", "avg_order_val"],
  ["conv_rate", "op_div1"],
  ["op_div1", "purch_cust_1"],
  ["op_div1", "acq_users"],
  ["orders_per_cust", "op_div2"],
  ["op_div2", "tot_orders_1"],
  ["op_div2", "purch_cust_2"],
  ["avg_order_val", "op_div3"],
  ["op_div3", "tot_gross_val"],
  ["op_div3", "tot_orders_2"],
].map(([source, target]) => ({ source, target }));

export const LEAF_IDS = new Set(
  NODES.filter((node) => !EDGES.some((edge) => edge.source === node.id)).map((node) => node.id)
);

// Nodes on the root-to-node path, inclusive (utils/graph_utils.py · ancestors_of).
export function ancestorsOf(nodeId) {
  const visited = new Set();
  const stack = [nodeId];
  while (stack.length) {
    const current = stack.pop();
    if (visited.has(current)) continue;
    visited.add(current);
    EDGES.filter((edge) => edge.target === current).forEach((edge) => stack.push(edge.source));
  }
  return visited;
}

// == Simulation deltas · graph_data.py · simulation_deltas()

function nodeDelta(scenarioValue, baselineValue, fmt, description) {
  const change = scenarioValue - baselineValue;
  const flat = Math.abs(change) < 1e-9;
  return {
    deltaValue: flat ? "" : fmt(Math.abs(change)),
    prevValue: fmt(baselineValue),
    direction: flat ? "flat" : change > 0 ? "up" : "down",
    labelPrefix: "Baseline:",
    description,
  };
}

function assumptionNote(baselineValue, scenarioValue, fmt) {
  if (Math.abs(scenarioValue - baselineValue) < 1e-9) {
    return "Held at the historical baseline in this scenario.";
  }
  return `Scenario assumption: ${fmt(baselineValue)} → ${fmt(scenarioValue)}.`;
}

// Delta badge per node. Counts compare against baseline rates on the same future cohort.
export function simulationDeltas(b, plan) {
  const before = fromBaseline(b);
  const deltas = {
    cust_val: nodeDelta(
      plan.customer_value, b.customer_value, money,
      `Scenario result: ${money(b.customer_value)} → ${money(plan.customer_value)} ` +
        `(= ${percent(plan.conversion_rate)} × ${decimal(plan.orders_per_purchasing_customer)} × ` +
        `${money(plan.average_order_value)}).`
    ),
    conv_rate: nodeDelta(
      plan.conversion_rate, b.conversion_rate, percent,
      assumptionNote(b.conversion_rate, plan.conversion_rate, percent)
    ),
    orders_per_cust: nodeDelta(
      plan.orders_per_purchasing_customer, b.orders_per_purchasing_customer, decimal,
      assumptionNote(b.orders_per_purchasing_customer, plan.orders_per_purchasing_customer, decimal)
    ),
    avg_order_val: nodeDelta(
      plan.average_order_value, b.average_order_value, money,
      assumptionNote(b.average_order_value, plan.average_order_value, money)
    ),
    acq_users: nodeDelta(
      plan.acquired_users, before.acquired_users, count,
      "Size of the future acquisition group; unchanged by the scenario."
    ),
    tot_gross_val: nodeDelta(
      plan.total_gross_order_value, before.total_gross_order_value, wholeMoney,
      `Computed consequence: ${count(plan.total_orders)} orders × ${money(plan.average_order_value)}.`
    ),
  };
  for (const id of ["purch_cust_1", "purch_cust_2"]) {
    deltas[id] = nodeDelta(
      plan.purchasing_customers, before.purchasing_customers, count,
      `Computed consequence: ${count(plan.acquired_users)} acquired users × ` +
        `${percent(plan.conversion_rate)}.`
    );
  }
  for (const id of ["tot_orders_1", "tot_orders_2"]) {
    deltas[id] = nodeDelta(
      plan.total_orders, before.total_orders, count,
      `Computed consequence: ${count(plan.purchasing_customers)} purchasing customers × ` +
        `${decimal(plan.orders_per_purchasing_customer)} orders each.`
    );
  }
  return deltas;
}

// == Transformation flows · graph_data.py: one per leaf; acquisitionStage() is the shared prefix.

const JOIN_ORDERS_DETAIL =
  "FROM acquired_users LEFT JOIN raw_orders USING (user_id)\n" +
  "A left join, so acquired users without orders are not dropped.";

function acquisitionStage(suffix, cohort) {
  const nodes = [
    { id: `raw_customers${suffix}`, label: "raw_customers", type: "source_table", x: 0, y: 0,
      description: "One row per user, with their acquisition date." },
    { id: `acq_users${suffix}`, label: "acquired_users", type: "filter_table", x: 1, y: 0,
      description: `The users acquired in ${cohort}, including those who never order.` },
    { id: `raw_orders${suffix}`, label: "raw_orders", type: "source_table", x: 0, y: 1.2,
      description: "One row per order, with its order date." },
    { id: `user_orders${suffix}`, label: "user_orders", type: "join", x: 2, y: 0.6,
      description:
        "Every order placed by an acquired user, alongside the acquired users who placed none." },
    { id: `age_day${suffix}`, label: "customer_age_day", type: "new_column", x: 3, y: 0.6,
      description:
        "Days between that user's own acquisition date and the order. Day 0 is the " +
        "acquisition day itself." },
    { id: `qualifying${suffix}`, label: "qualifying_orders", type: "filter_table", x: 4, y: 0.6,
      description: "Orders placed inside each user's own first 90 days." },
  ];
  const edges = [
    { source: `raw_customers${suffix}`, target: `acq_users${suffix}`, label: "Filter applied",
      description:
        `WHERE acquisition_date IN ${cohort}\n` +
        "Every acquired user is kept, including those who never order, so " +
        "non-purchasers stay in the denominator of the metric." },
    { source: `acq_users${suffix}`, target: `user_orders${suffix}`, label: "Join",
      description: JOIN_ORDERS_DETAIL },
    { source: `raw_orders${suffix}`, target: `user_orders${suffix}`, label: "Join",
      description: JOIN_ORDERS_DETAIL },
    { source: `user_orders${suffix}`, target: `age_day${suffix}`, label: "New Column",
      description:
        "SELECT DATEDIFF(order_date, acquisition_date) AS customer_age_day\n" +
        "Whole days, so the boundary falls at midnight rather than at the acquisition " +
        "time of day." },
    { source: `age_day${suffix}`, target: `qualifying${suffix}`, label: "Filter applied",
      description:
        "WHERE customer_age_day BETWEEN 0 AND 89\n" +
        "Day 0 is the acquisition day, so this is the first 90 days. Each user is " +
        "observed from their own acquisition date, never by calendar date, so users " +
        "acquired later in the month get the same length of window." },
  ];
  return [nodes, edges];
}

function acquiredUsersFlow(cohort) {
  return [
    [
      { id: "raw_customers_au", label: "raw_customers", type: "source_table", x: 0, y: 0,
        description: "One row per user, with their acquisition date." },
      { id: "acq_users_au", label: "acquired_users", type: "filter_table", x: 1, y: 0,
        description: `The users acquired in ${cohort}, including those who never order.` },
      { id: "acq_users_output", label: "Acquired Users", type: "output", x: 2, y: 0,
        description: "The denominator of the metric: every user acquired in the reference period." },
    ],
    [
      { source: "raw_customers_au", target: "acq_users_au", label: "Filter applied",
        description:
          `WHERE acquisition_date IN ${cohort}\n` +
          "The reference acquisition period: which users belong to this historical group." },
      { source: "acq_users_au", target: "acq_users_output", label: "Distinct Count",
        description:
          "COUNT(DISTINCT user_id)\n" +
          "Counted over the acquisition population, before filtering to purchasers, so " +
          "users who never order are counted here." },
    ],
  ];
}

function purchasingCustomersFlow(suffix, cohort) {
  const [nodes, edges] = acquisitionStage(suffix, cohort);
  nodes.push({ id: `purch_cust_output${suffix}`, label: "Purchasing Customers", type: "output",
    x: 5, y: 0.6, description: "Acquired users with at least one order in their first 90 days." });
  edges.push({ source: `qualifying${suffix}`, target: `purch_cust_output${suffix}`,
    label: "Distinct Count",
    description:
      "COUNT(DISTINCT user_id)\n" +
      "Counted over the qualifying orders: a user counts once however many orders they placed." });
  return [nodes, edges];
}

function totalOrdersFlow(suffix, cohort) {
  const [nodes, edges] = acquisitionStage(suffix, cohort);
  nodes.push({ id: `tot_orders_output${suffix}`, label: "Total Orders", type: "aggregation",
    x: 5, y: 0.6, description: "Orders placed by the acquisition group in their first 90 days." });
  edges.push({ source: `qualifying${suffix}`, target: `tot_orders_output${suffix}`,
    label: "Distinct Count",
    description:
      "COUNT(DISTINCT order_id)\nCounted over the qualifying orders of the acquisition group." });
  return [nodes, edges];
}

function grossValueFlow(cohort) {
  const [nodes, edges] = acquisitionStage("_gv", cohort);
  nodes.push(
    { id: "raw_order_items_gv", label: "raw_order_items", type: "source_table", x: 0, y: 2.4,
      description: "One row per order line." },
    { id: "raw_products_gv", label: "raw_products", type: "source_table", x: 0, y: 3.6,
      description: "Product price and supply cost." },
    { id: "priced_lines_gv", label: "priced_order_items", type: "join", x: 3, y: 3.0,
      description: "Order lines with their product's revenue and cost attached." },
    { id: "gross_value_gv", label: "gross_value", type: "new_column", x: 4, y: 3.0,
      description: "What an order line sold for, less what it cost to make." },
    { id: "qualifying_lines_gv", label: "qualifying_order_lines", type: "join", x: 5, y: 1.8,
      description: "The order lines belonging to qualifying orders." },
    { id: "tot_gross_output_gv", label: "Total Gross Order Value", type: "aggregation", x: 6, y: 1.8,
      description: "Value generated by the acquisition group in their first 90 days." }
  );
  const productsDetail =
    "FROM raw_order_items JOIN raw_products USING (product_id)\n" +
    "Enriches each order line with the product's revenue and cost.";
  const linesDetail =
    "FROM qualifying_orders JOIN gross_value USING (order_id)\n" +
    "Keeps only the lines belonging to orders inside each user's first 90 days.";
  edges.push(
    { source: "raw_order_items_gv", target: "priced_lines_gv", label: "Join", description: productsDetail },
    { source: "raw_products_gv", target: "priced_lines_gv", label: "Join", description: productsDetail },
    { source: "priced_lines_gv", target: "gross_value_gv", label: "New Column",
      description: "SELECT (revenue - cost) AS gross_value\nComputed for each order line." },
    { source: "qualifying_gv", target: "qualifying_lines_gv", label: "Join", description: linesDetail },
    { source: "gross_value_gv", target: "qualifying_lines_gv", label: "Join", description: linesDetail },
    { source: "qualifying_lines_gv", target: "tot_gross_output_gv", label: "Sum",
      description:
        "SUM(gross_value)\nSummed over every qualifying order line of the acquisition group." }
  );
  return [nodes, edges];
}

const FLOW_BUILDERS = {
  acq_users: acquiredUsersFlow,
  purch_cust_1: (cohort) => purchasingCustomersFlow("_pc1", cohort),
  purch_cust_2: (cohort) => purchasingCustomersFlow("_pc2", cohort),
  tot_orders_1: (cohort) => totalOrdersFlow("_to1", cohort),
  tot_orders_2: (cohort) => totalOrdersFlow("_to2", cohort),
  tot_gross_val: grossValueFlow,
};

// [nodes, edges] for one leaf, or empty lists (transformation_flow).
export function transformationFlow(leafId, cohortLabel) {
  const builder = FLOW_BUILDERS[leafId];
  return builder ? builder(cohortLabel) : [[], []];
}
