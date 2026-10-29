// Draws CLUE's three graphs as HTML nodes over SVG edges. Port of demo/utils/graph_builders.py + graph_styles.py (was streamlit_flow).

import { html } from "./common.js";
import { EDGES, LEAF_IDS, NODES, ancestorsOf, transformationFlow } from "./clue-model.js";

export const COLORS = {
  root_bg: "#FCE4C6", root_border: "#F4A23A", root_text: "#C97A10",
  op_bg: "#F5E6C8", op_border: "#C9A84C", op_text: "#8B6914",
  metric_bg: "#EEF0FF", metric_border: "#6B72D9", metric_text: "#2A2E8C",
  ratio_bg: "#E8F8EF", ratio_border: "#3DAA6B", ratio_text: "#1A6640",
  hl_bg: "#DBEAFE", hl_border: "#2563EB", hl_text: "#1D4ED8",
  edge_normal: "#CBD5E1", edge_hl: "#2563EB",
  edge_label_text: "#0000FF", edge_label_bg: "#FFFFFF", edge_label_border: "#FFA500",
  delta_up: "#16A34A", delta_down: "#DC2626", delta_flat: "#9CA3AF",
};

const TRANSFORMATION_EDGE_COLOR = "#94A3B8";
const SVG_NS = "http://www.w3.org/2000/svg";
export const STATIC_URL = "/static";

// == Stage: pannable surface scaled to fit its panel (streamlit_flow fit_view, pan_on_drag)

function createStage(container, height) {
  container.innerHTML = "";
  const viewport = document.createElement("div");
  viewport.className = "flow-viewport";
  viewport.style.height = `${height}px`;

  const stage = document.createElement("div");
  stage.className = "flow-stage";

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.classList.add("flow-edges");
  svg.innerHTML = `<defs>${[COLORS.edge_normal, COLORS.edge_hl, TRANSFORMATION_EDGE_COLOR]
    .map(
      (color) =>
        `<marker id="arrow-${color.slice(1)}" viewBox="0 0 10 10" refX="9" refY="5"
           markerWidth="12.5" markerHeight="12.5" markerUnits="userSpaceOnUse"
           orient="auto-start-reverse">
           <path d="M0,0 L10,5 L0,10 z" fill="${color}"/>
         </marker>`
    )
    .join("")}</defs>`;

  stage.append(svg);
  viewport.append(stage);
  container.append(viewport);
  enablePan(viewport, stage);
  return { viewport, stage, svg };
}

// Scales and centres the drawing in its panel, never above 1:1.
function fit(viewport, stage, bounds, padding = 0.1) {
  const width = bounds.right - bounds.left;
  const height = bounds.bottom - bounds.top;
  const available = viewport.getBoundingClientRect();
  const scale = Math.min(
    1,
    (available.width * (1 - padding)) / width,
    (available.height * (1 - padding)) / height
  );
  const x = (available.width - width * scale) / 2 - bounds.left * scale;
  const y = (available.height - height * scale) / 2 - bounds.top * scale;
  stage.dataset.x = x;
  stage.dataset.y = y;
  stage.dataset.scale = scale;
  stage.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
}

function enablePan(viewport, stage) {
  let start = null;
  viewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    start = {
      x: event.clientX, y: event.clientY,
      ox: Number(stage.dataset.x || 0), oy: Number(stage.dataset.y || 0),
      moved: false, id: event.pointerId,
    };
  });
  viewport.addEventListener("pointermove", (event) => {
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (!start.moved && Math.hypot(dx, dy) < 4) return;
    if (!start.moved) {
      start.moved = true;
      viewport.setPointerCapture(start.id);
      viewport.classList.add("is-panning");
    }
    stage.dataset.x = start.ox + dx;
    stage.dataset.y = start.oy + dy;
    stage.style.transform =
      `translate(${start.ox + dx}px, ${start.oy + dy}px) scale(${stage.dataset.scale})`;
  });
  const end = () => {
    if (start?.moved) {
      // Ignore the click that ends a drag.
      viewport.addEventListener("click", (e) => e.stopPropagation(), { capture: true, once: true });
    }
    start = null;
    viewport.classList.remove("is-panning");
  };
  viewport.addEventListener("pointerup", end);
  viewport.addEventListener("pointercancel", end);
}

// Re-fits when the panel's width changes.
function refitOnResize(viewport, stage, bounds) {
  let width = viewport.clientWidth;
  const observer = new ResizeObserver(() => {
    if (!viewport.isConnected) return observer.disconnect();
    if (viewport.clientWidth === width) return;
    width = viewport.clientWidth;
    fit(viewport, stage, bounds);
  });
  observer.observe(viewport);
}

// == Layout helpers · graph_builders.py

function addNode(stage, { id, content, className, style = {}, tooltip }) {
  const element = document.createElement("div");
  element.className = `flow-node ${className}`;
  element.dataset.id = id;
  if (tooltip) element.dataset.tooltip = tooltip;
  Object.assign(element.style, style);
  element.innerHTML = content;
  stage.append(element);
  return element;
}

// Left x and width per logical column; `gaps` widens chosen boundaries (_column_layout).
function columnLayout(nodes, widths, xOffset, xGap, gaps = {}) {
  const columns = [...new Set(nodes.map((node) => node.x))].sort((a, b) => a - b);
  const left = new Map();
  const width = new Map();
  let x = xOffset;
  for (const column of columns) {
    left.set(column, x);
    width.set(
      column,
      Math.max(...nodes.filter((node) => node.x === column).map((node) => widths.get(node.id)))
    );
    x += width.get(column) + Math.max(xGap, gaps[column] ?? 0);
  }
  return { left, width };
}

// Step edge path (React Flow smoothstep): right, turn at turnX, right.
function stepPath(sx, sy, tx, ty, turnX, radius = 5) {
  if (Math.abs(ty - sy) < 0.5) return `M${sx},${sy} L${tx},${ty}`;
  const r = Math.min(radius, Math.abs(ty - sy) / 2, Math.abs(turnX - sx), Math.abs(tx - turnX));
  const down = ty > sy ? 1 : -1;
  return [
    `M${sx},${sy}`,
    `L${turnX - r},${sy}`,
    `Q${turnX},${sy} ${turnX},${sy + r * down}`,
    `L${turnX},${ty - r * down}`,
    `Q${turnX},${ty} ${turnX + r},${ty}`,
    `L${tx},${ty}`,
  ].join(" ");
}

function addEdge(svg, d, { color, width = 1.5, markerEnd = false, markerStart = false, animated = false }) {
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", width);
  const marker = `url(#arrow-${color.slice(1)})`;
  if (markerEnd) path.setAttribute("marker-end", marker);
  if (markerStart) path.setAttribute("marker-start", marker);
  if (animated) path.classList.add("is-animated");
  svg.append(path);
}

function sizeSvg(svg, bounds) {
  svg.setAttribute("width", bounds.right + 40);
  svg.setAttribute("height", bounds.bottom + 40);
}

function boundsOf(boxes) {
  return boxes.reduce(
    (b, box) => ({
      left: Math.min(b.left, box.x),
      top: Math.min(b.top, box.y),
      right: Math.max(b.right, box.x + box.w),
      bottom: Math.max(b.bottom, box.y + box.h),
    }),
    { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity }
  );
}

// == Metric tree: provenance and simulation graphs

function operatorSvg(symbol, highlighted = false) {
  const color = highlighted ? COLORS.hl_text : COLORS.op_text;
  const bg = highlighted ? COLORS.hl_bg : COLORS.op_bg;
  const border = highlighted ? COLORS.hl_border : COLORS.op_border;
  return `<svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
      <g transform="rotate(45 20 20)">
        <rect x="6" y="6" width="28" height="28" fill="${bg}" stroke="${border}" stroke-width="2" rx="2"/>
      </g>
      <text x="20" y="21" font-size="20" font-weight="700" text-anchor="middle"
            dominant-baseline="middle" fill="${color}">${symbol}</text>
    </svg>`;
}

function labelText(node) {
  if (node.type === "metric" && node.symbol === "#") return html`#&nbsp;&nbsp;${node.label}`.__raw;
  if (node.symbol) return html`${node.symbol}&nbsp;&nbsp;${node.label}`.__raw;
  return html`${node.label}`.__raw;
}

function deltaBadge(delta) {
  const [arrow, color] = {
    up: ["↑", COLORS.delta_up],
    down: ["↓", COLORS.delta_down],
    flat: ["—", COLORS.delta_flat],
  }[delta.direction];
  const previous = html`<span class="flow-delta-prev">(${delta.labelPrefix}&nbsp;${delta.prevValue})</span>`;
  const value =
    delta.direction === "flat"
      ? html`<span class="flow-delta-value" style="color:${color}">${arrow}</span>&nbsp;`
      : html`<span class="flow-delta-value" style="color:${color}">${arrow}&nbsp;${delta.deltaValue}</span>&nbsp;`;
  return html`<span class="flow-delta">${value}${previous}</span>`.__raw;
}

// mode "provenance": clickable leaves + path highlight; "simulation": delta badges, arrows back to root.
function renderMetricTree(container, { mode, height, highlighted, values = {}, deltas = {}, onSelect }) {
  const simulation = mode === "simulation";
  const Y_SCALE = simulation ? 100 : 85;
  const X_OFFSET = 10;
  const Y_OFFSET = simulation ? 70 : 60;
  const X_GAP = 45;
  const NODE_HEIGHT = simulation ? 65 : 50;

  const { viewport, stage, svg } = createStage(container, height);
  const onPath = highlighted ? ancestorsOf(highlighted) : new Set();

  const elements = new Map();
  for (const node of NODES) {
    const isHl = onPath.has(node.id);
    const delta = deltas[node.id];
    let content;
    let tooltip;
    if (node.type === "operator") {
      content = operatorSvg(node.symbol, isHl);
    } else if (simulation && delta) {
      content = `<div class="flow-node-stack">${labelText(node)}${deltaBadge(delta)}</div>`;
      tooltip = delta.description;
    } else {
      content = labelText(node);
      const value = values[node.id];
      tooltip = [node.description, value ? `Historical baseline: ${value}` : null]
        .filter(Boolean)
        .join("\n");
    }
    const clickable = !simulation && LEAF_IDS.has(node.id);
    const element = addNode(stage, {
      id: node.id,
      content,
      tooltip,
      className: [
        `is-${node.type}`,
        isHl && node.type !== "operator" ? "is-highlighted" : "",
        clickable ? "is-clickable" : "",
        simulation ? "is-sim" : "",
      ].join(" "),
      style: { height: `${NODE_HEIGHT}px` },
    });
    if (clickable) {
      element.tabIndex = 0;
      element.setAttribute("role", "button");
      element.setAttribute("aria-pressed", String(node.id === highlighted));
      element.addEventListener("click", () => onSelect?.(node.id));
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect?.(node.id);
        }
      });
    }
    elements.set(node.id, element);
  }

  const widths = new Map([...elements].map(([id, el]) => [id, el.offsetWidth]));
  const { left, width } = columnLayout(NODES, widths, X_OFFSET, X_GAP);

  const boxes = new Map();
  for (const node of NODES) {
    const box = {
      x: left.get(node.x),
      y: Y_OFFSET + node.y * Y_SCALE,
      w: widths.get(node.id),
      h: NODE_HEIGHT,
    };
    boxes.set(node.id, box);
    Object.assign(elements.get(node.id).style, { left: `${box.x}px`, top: `${box.y}px` });
  }

  for (const edge of EDGES) {
    const s = boxes.get(edge.source);
    const t = boxes.get(edge.target);
    const sx = s.x + s.w;
    const sy = s.y + s.h / 2;
    const tx = t.x;
    const ty = t.y + t.h / 2;
    const isHl = onPath.has(edge.source) && onPath.has(edge.target);
    addEdge(svg, stepPath(sx, sy, tx, ty, (sx + tx) / 2), {
      color: isHl ? COLORS.edge_hl : COLORS.edge_normal,
      width: isHl ? 2.5 : 1.5,
      markerEnd: !simulation,
      markerStart: simulation,
      animated: isHl,
    });
  }

  // Right edge = last column's right edge.
  const bounds = boundsOf([...boxes.values()]);
  bounds.right = Math.max(...[...left].map(([column, x]) => x + width.get(column)));
  sizeSvg(svg, bounds);
  fit(viewport, stage, bounds);
  refitOnResize(viewport, stage, bounds);
}

export function renderProvenanceGraph(container, { highlighted, values, onSelect }) {
  renderMetricTree(container, { mode: "provenance", height: 400, highlighted, values, onSelect });
}

export function renderSimulationGraph(container, deltas) {
  renderMetricTree(container, { mode: "simulation", height: 460, deltas });
}

// == Transformation graph · build_transformation_flow_elements()

const TRANSFORMATION_NODE_HEIGHT = 84;

const TRANSFORMATION_TEXT = {
  source_table: "#2F2F2F",
  filter_table: "#256AFF",
  new_column: "#256AFF",
  join: "#4E9D26",
  aggregation: "#900B09",
  output: "#392C05",
};

const TRANSFORMATION_ICON = {
  source_table: "source_table.png",
  filter_table: "filter_table.png",
  new_column: "new_column.png",
  join: "join.png",
  aggregation: "output.png",
  output: "output.png",
};

export function renderTransformationGraph(container, leafId, cohortLabel) {
  const [nodes, edges] = transformationFlow(leafId, cohortLabel);
  if (!nodes.length) {
    container.innerHTML = html`<div class="flow-empty">
      Click a leaf metric in the provenance graph to see how it is computed from
      the raw source tables.</div>`;
    return;
  }

  const TY_SCALE = 140;
  const TX_OFFSET = 20;
  const TY_OFFSET = 40;
  const TX_GAP = 45;

  const { viewport, stage, svg } = createStage(container, 300);

  const elements = new Map();
  for (const node of nodes) {
    elements.set(
      node.id,
      addNode(stage, {
        id: node.id,
        tooltip: node.description,
        className: "is-transformation",
        style: { height: `${TRANSFORMATION_NODE_HEIGHT}px`, color: TRANSFORMATION_TEXT[node.type] },
        content: html`<img src="${STATIC_URL}/${TRANSFORMATION_ICON[node.type]}" width="50"
            height="50" alt=""><span>${node.label}</span>`.__raw,
      })
    );
  }

  // Operation chips, as HTML so they can carry tooltips.
  const chips = edges.map((edge) => {
    const chip = document.createElement("div");
    chip.className = "flow-chip";
    chip.textContent = edge.label;
    if (edge.description) chip.dataset.tooltip = edge.description;
    stage.append(chip);
    return chip;
  });

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const widths = new Map(
    nodes.map((node) => [node.id, Math.max(elements.get(node.id).offsetWidth, 130)])
  );

  // Widen the boundary before each target column to fit its chip.
  const gaps = {};
  edges.forEach((edge, i) => {
    const column = nodeById.get(edge.target).x - 1;
    gaps[column] = Math.max(gaps[column] ?? 0, chips[i].offsetWidth + 24);
  });
  const { left, width } = columnLayout(nodes, widths, TX_OFFSET, TX_GAP, gaps);

  // Nodes take their column's width.
  const boxes = new Map();
  for (const node of nodes) {
    const box = {
      x: left.get(node.x),
      y: TY_OFFSET + node.y * TY_SCALE,
      w: width.get(node.x),
      h: TRANSFORMATION_NODE_HEIGHT,
    };
    boxes.set(node.id, box);
    Object.assign(elements.get(node.id).style, {
      left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px`,
    });
  }

  // All edges into a target turn mid-way across the boundary before it (was the waypoint trick).
  const chipBoxes = [];
  edges.forEach((edge, i) => {
    const s = boxes.get(edge.source);
    const t = boxes.get(edge.target);
    const target = nodeById.get(edge.target);
    const sx = s.x + s.w;
    const sy = s.y + s.h / 2;
    const tx = t.x;
    const ty = t.y + t.h / 2;
    const before = target.x - 1;
    const turnX = left.has(before) ? (left.get(before) + width.get(before) + tx) / 2 : (sx + tx) / 2;

    addEdge(svg, stepPath(sx, sy, tx, ty, turnX), {
      color: TRANSFORMATION_EDGE_COLOR,
      markerEnd: true,
    });

    const chip = chips[i];
    const cw = chip.offsetWidth;
    const ch = chip.offsetHeight;
    const cy = (sy + ty) / 2;
    chip.style.left = `${turnX - cw / 2}px`;
    chip.style.top = `${cy - ch / 2}px`;
    chipBoxes.push({ x: turnX - cw / 2, y: cy - ch / 2, w: cw, h: ch });
  });

  const bounds = boundsOf([...boxes.values(), ...chipBoxes]);
  sizeSvg(svg, bounds);
  // Panel height grows with the flow (300–540px) so tall flows stay readable.
  const widthScale = Math.min(1, (viewport.clientWidth * 0.9) / (bounds.right - bounds.left));
  const wanted = ((bounds.bottom - bounds.top) * widthScale) / 0.9;
  viewport.style.height = `${Math.round(Math.min(540, Math.max(300, wanted)))}px`;
  fit(viewport, stage, bounds);
  refitOnResize(viewport, stage, bounds);
}

// == Legends · graph_styles.py · legend_style_html(), transformation_legend_style_html()

export function provenanceLegendHtml() {
  return html`
    <div class="flow-legend">
      <span><span class="legend-chip" style="background:${COLORS.root_bg};border:3px solid ${COLORS.root_border};color:${COLORS.root_text};font-weight:700;border-radius:4px">90-Day Customer Value</span> Root</span>
      <span><span class="legend-chip" style="background:${COLORS.op_bg};border:1.5px solid ${COLORS.op_border};color:${COLORS.op_text};border-radius:4px">× ÷</span> Operator</span>
      <span><span class="legend-chip" style="background:${COLORS.ratio_bg};border:1.5px solid ${COLORS.ratio_border};color:${COLORS.ratio_text}">% Metric</span> Ratio</span>
      <span><span class="legend-chip" style="background:${COLORS.metric_bg};border:1.5px solid ${COLORS.metric_border};color:${COLORS.metric_text}"># Metric</span> Count/value</span>
      <span><span class="legend-line" style="background:${COLORS.edge_hl}"></span> Highlighted path</span>
    </div>`;
}

export function transformationLegendHtml() {
  const items = [
    ["source_table", "Source Table"],
    ["filter_table", "Row Removal"],
    ["new_column", "New Column"],
    ["join", "Join"],
    ["output", "Output Metric"],
  ];
  return html`
    <div class="flow-legend">
      ${items.map(
        ([type, label]) => html`<span><img src="${STATIC_URL}/${type}.png" width="24" height="24" alt="">${label}</span>`
      )}
      <span><span class="flow-chip is-static">Operation</span> Operation</span>
    </div>`;
}
