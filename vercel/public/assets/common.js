// Shared plumbing for both pages: data loading, month maths, number formatting, tooltip. No metric rules live here.

export const WINDOW_DAYS = 90;
export const WINDOW_LABEL = `${WINDOW_DAYS}-Day`;

// Default reference period, as in components/filters.py and demo/data/metrics.py.
export const DEFAULT_START = "2024-01";
export const DEFAULT_END = "2024-06";

// CLUE's path on this site (replaces CLUE_URL in baseline_dashboard/clue.py).
export const CLUE_PATH = "/clue/";

// == Data: fetches the JSON written by scripts/export_data.py

export class DataMissingError extends Error {}

const DATA_ROOT = "/data";

export async function loadCohorts() {
  const response = await fetch(`${DATA_ROOT}/cohorts.json`, { cache: "no-cache" });
  if (!response.ok) {
    throw new DataMissingError(
      "The exported data source is missing (data/cohorts.json). Build it with " +
        "`python -m datasource.build` in baseline_dashboard/, then run " +
        "`python vercel/scripts/export_data.py` from the repo root."
    );
  }
  return response.json();
}

const monthCache = new Map();

// Underlying rows for one month, fetched once and cached (datasource/loader.py).
export function loadMonthRows(month) {
  if (!monthCache.has(month)) {
    monthCache.set(
      month,
      fetch(`${DATA_ROOT}/months/${month}.json`).then((response) => {
        if (!response.ok) throw new Error(`No underlying rows for ${month}.`);
        return response.json();
      })
    );
  }
  return monthCache.get(month);
}

// == Months: "YYYY-MM" strings (pandas Period in the Python apps)

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export function ordinal(month) {
  const [year, number] = month.split("-").map(Number);
  return year * 12 + (number - 1);
}

export function fromOrdinal(value) {
  const year = Math.floor(value / 12);
  const number = (value % 12) + 1;
  return `${year}-${String(number).padStart(2, "0")}`;
}

export function addMonths(month, count) {
  return fromOrdinal(ordinal(month) + count);
}

// 'Jun 2024'
export function monthLabel(month) {
  const [year, number] = month.split("-").map(Number);
  return `${MONTH_NAMES[number - 1]} ${year}`;
}

// 'Jan-Jun 2024', 'Nov 2023-Feb 2024' or 'Jun 2024' (CohortFilter.label).
export function periodLabel(start, end) {
  if (start === end) return monthLabel(start);
  const [startYear] = start.split("-");
  const [endYear] = end.split("-");
  if (startYear === endYear) {
    return `${monthLabel(start).slice(0, 3)}-${monthLabel(end)}`;
  }
  return `${monthLabel(start)}-${monthLabel(end)}`;
}

// Parses a YYYY-MM query parameter; null when missing or invalid.
export function parseMonth(raw) {
  if (!raw) return null;
  const match = /^(\d{4})-(\d{1,2})$/.exec(String(raw).trim());
  if (!match) return null;
  const number = Number(match[2]);
  if (number < 1 || number > 12) return null;
  return `${match[1]}-${String(number).padStart(2, "0")}`;
}

// == Formatting: money/percent/count/decimal from metrics/registry.py

function grouped(value, digits) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

const isMissing = (value) => value === null || value === undefined || Number.isNaN(value);

export function money(value) {
  if (isMissing(value)) return "—";
  return Math.abs(value) < 1000 ? `$${grouped(value, 2)}` : `$${grouped(value, 0)}`;
}

export function wholeMoney(value) {
  return isMissing(value) ? "—" : `$${grouped(value, 0)}`;
}

export function percent(value) {
  return isMissing(value) ? "—" : `${grouped(value * 100, 1)}%`;
}

export function count(value) {
  return isMissing(value) ? "—" : grouped(value, 0);
}

export function decimal(value) {
  return isMissing(value) ? "—" : grouped(value, 1);
}

export function safeDivide(numerator, denominator) {
  return denominator ? numerator / denominator : NaN;
}

// == DOM helpers

export function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// Marks a string as safe markup.
export const raw = (text) => ({ __raw: String(text), toString: () => String(text) });

function interpolate(value) {
  if (Array.isArray(value)) return value.map(interpolate).join("");
  if (value?.__raw !== undefined) return value.__raw;
  return escapeHtml(value ?? "");
}

// Tagged template: escapes interpolations except raw() and nested html``.
export function html(strings, ...values) {
  return raw(
    strings.reduce((out, chunk, index) => out + interpolate(values[index - 1]) + chunk)
  );
}

// One floating tooltip for every [data-tooltip] element (demo/utils/tooltip_overlay.py).
export function installTooltip() {
  if (document.getElementById("tooltip")) return;
  const tip = document.createElement("div");
  tip.id = "tooltip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);

  let current = null;
  const place = (event) => {
    const margin = 14;
    const { innerWidth, innerHeight } = window;
    const rect = tip.getBoundingClientRect();
    let x = event.clientX + margin;
    let y = event.clientY + margin;
    if (x + rect.width > innerWidth - 8) x = event.clientX - rect.width - margin;
    if (y + rect.height > innerHeight - 8) y = event.clientY - rect.height - margin;
    tip.style.left = `${Math.max(8, x)}px`;
    tip.style.top = `${Math.max(8, y)}px`;
  };

  document.addEventListener("pointerover", (event) => {
    const target = event.target.closest?.("[data-tooltip]");
    if (target === current) return;
    current = target;
    if (!target) {
      tip.classList.remove("is-visible");
      return;
    }
    tip.textContent = target.dataset.tooltip;
    tip.classList.add("is-visible");
    place(event);
  });
  document.addEventListener("pointermove", (event) => {
    if (current) place(event);
  });
  document.addEventListener("pointerleave", () => {
    current = null;
    tip.classList.remove("is-visible");
  });
}

// Full-page message shown when data/ has not been exported.
export function renderFatal(container, error) {
  container.innerHTML = html`
    <div class="fatal">
      <h2>Data source not available</h2>
      <p>${error.message}</p>
    </div>`;
}
