# CLUE: Making Sense of the Numbers on a Dashboard

## The problem

Most organizations run on dashboards. Open one and you'll see a set of
headline numbers — revenue, conversion rate, customer value — each paired with
an indicator of how it moved since the last reporting period. These numbers
inform real decisions: whether to increase a marketing budget, whether a
product change worked, whether a team met its goal.

Dashboards are generally better at *reporting* a number than *explaining* it.
When a metric declines and someone asks why, or a stakeholder asks how to grow
it by 20% next quarter, the dashboard itself rarely provides an answer. The
underlying explanation — the formulas, the source data, and the chain of
transformations that produced the number on screen — typically lives in SQL
scripts, spreadsheets, or the memory of whoever built the dashboard originally.
An analyst who inherits that dashboard has to reverse-engineer all of it by
hand before they can answer even a basic question about what drives the metric.

**CLUE** was built to address this gap. It works alongside a dashboard and
answers the two questions dashboards rarely do: *how is this number actually
calculated?* and *what would need to change to move it?*

## The two components

This project consists of two applications that work together:

- **The Customer Value Dashboard** — a conventional business dashboard. It
  presents KPI cards and charts for an e-commerce business, comparable to what
  most companies already use for internal reporting.
- **CLUE** — a companion tool, opened from any metric card on the dashboard,
  that shows where a number comes from and lets a user explore how changing it
  would work.

The two are kept intentionally separate: the dashboard functions on its own,
and CLUE is the explanatory layer a user opens only when they need it.

## What CLUE does

**1. It visualizes how a metric is composed.** Most business metrics are built
from smaller ones. Customer value, for example, is not a single value pulled
from a database — it is the product of a conversion rate, an order count, and
an average order size, each of which is in turn derived from more basic
counts. CLUE renders this as a tree: the metric under review sits at the top,
its immediate components sit one level below, and the user can expand further
levels down to the raw data. A user arrives at CLUE already holding a specific
metric from the dashboard, so this view opens directly on that metric's
composition rather than requiring a separate search step.

**2. It exposes the underlying data transformations.** For users who need more
detail than "these values are multiplied together," CLUE can open the
underlying data pipeline: the joins, filters, and calculations that turned raw
records into a given metric component. Hovering over any step surfaces a
plain-language description (and, where relevant, the underlying query logic)
without requiring access to a code editor.

**3. It supports manual "what-if" exploration.** This is what turns CLUE from
a diagram into a planning tool. A user sets a growth goal — a target percentage
lift over the historical baseline — and then adjusts three sliders
(conversion rate, orders per purchasing customer, average order value)
independently to build a scenario. Each slider moves on its own; nothing
rebalances automatically to hit the target, so a scenario is free to land
above or below the goal, and the user sees which as they adjust. A "best
observed" card — each factor at its best historical month, combined — is
offered as a starting point, since a composite drawn from real history is a
more grounded place to begin than an arbitrary guess.

**4. It makes the implied data changes visible.** A high-level scenario such
as a higher conversion rate or larger average order value can be difficult to
reason about on its own. When a user selects a scenario, CLUE translates those
assumptions into the concrete changes they imply in the underlying data — such
as how many more purchasing customers, orders, or dollars of gross order value
would be needed — and visualizes how those changes propagate through the metric
tree to produce the resulting 90-Day Customer Value. This connects a planning
assumption back to the data quantities behind the metric, so the user can see
not only the projected outcome but what would have to be different underneath
it. Saved scenarios can still be revisited for reference or comparison, but
comparison is a supporting interaction rather than the primary purpose of this
view.

## Simulator design rationale

The simulator is designed as a **scenario exploration tool rather than an
optimizer or strategy recommender**. Its purpose is to help users navigate
possible ways a target metric could change and gather enough evidence to decide
which directions are worth investigating further.

**Goal setting — defines the direction of exploration.** The growth goal gives
the user a reference point for the analysis, such as *“What would it take for
90-Day Customer Value to increase by 15%?”* It focuses the exploration without
defining a single correct answer or requiring every scenario to hit the target
exactly.

**Sliders — represent scenario assumptions, not actions.** Adjusting Purchase
Conversion Rate from 40% to 42%, for example, means *“show me what the business
would look like if conversion were 42%,”* not *“increase conversion to 42%.”*
The three sliders let users explore where improvement might come from across
conversion, purchase frequency, and order value.

**Best-observed scenario — provides a grounded starting point.** It gives users a
reference based on values that have appeared in the historical data, reducing
the need to begin from arbitrary guesses. It is a starting point for
exploration, not a recommendation or proof of real-world feasibility.

**Scenario implications and propagation — make assumptions concrete.** For a
selected scenario, CLUE translates high-level assumptions into changes in
Purchasing Customers, Total Orders, and Total Gross Order Value, then shows how
those changes propagate through the metric tree to the resulting 90-Day
Customer Value. This helps users understand both *what the scenario implies*
and *why it produces the result shown*.

Taken together, these components support a progression from a broad goal, to
possible metric configurations, to their underlying implications. CLUE does not
decide which scenario is “best”; the intended endpoint is for the user to judge
which direction, if any, is worth considering further.

## The demonstration dataset

CLUE is demonstrated using a real, publicly available e-commerce dataset (the
open-source "Jaffle Shop" dataset), which includes customers, orders, order
line items, products, supply costs, and stores. Using real transaction data,
rather than a synthetic example, is what makes questions like "why did this
number move" and "how do I reach this target" concrete rather than
hypothetical.

---

## Metric reference

Everything the dashboard and CLUE display is derived from the definitions
below, listed from the headline metric down to the raw fields it is built
from, since each metric is defined in terms of the ones beneath it.

Every metric below describes a single **acquisition cohort** — the group of
users who joined in one calendar month — observed over a fixed **90-day
window measured from each user's own acquisition date**, rather than a shared
calendar date. This matters because it means a user who joined late in a
month is still followed for a full 90 days from their own join date, so no
cohort is disadvantaged by when in the month its users happened to join.

### 90-Day Customer Value (headline metric)

**Definition.** The average value generated per acquired user during their
first 90 days, counting every user acquired in the cohort, including those who
never placed an order.

**Formula.**

```
90-Day Customer Value
    = 90-Day Purchase Conversion Rate
        × Orders per Purchasing Customer
        × Average Order Value

Equivalently:

90-Day Customer Value = Total Gross Order Value / Acquired Users
```

### 90-Day Purchase Conversion Rate

**Definition.** The percentage of acquired users who place at least one order
within their first 90 days after acquisition.

**Formula.**

```
Conversion Rate = Purchasing Customers / Acquired Users
```

### Orders per Purchasing Customer

**Definition.** The average number of orders placed by a customer who ordered
at least once within the 90-day window. Users who never ordered are excluded
from this average, though they are still counted in the conversion rate above.

**Formula.**

```
Orders per Purchasing Customer = Total Orders / Purchasing Customers
```

### Average Order Value (AOV)

**Definition.** The average gross value of a single qualifying order — what
the order was worth after subtracting the cost of the items in it.

**Formula.**

```
Average Order Value = Total Gross Order Value / Total Orders
```

### Acquired Users

**Definition.** The number of users whose account was created within the
acquisition month being described, regardless of whether they ever placed an
order. This is the denominator that anchors every rate above, and is what
makes customer value a "per acquired user" figure rather than a "per
customer" figure.

**Formula.**

```
Acquired Users = COUNT(DISTINCT user_id) for users acquired in the given month
```

### Purchasing Customers

**Definition.** The subset of acquired users who placed at least one order
within their own first 90 days.

**Formula.**

```
Purchasing Customers = COUNT(DISTINCT user_id) with ≥ 1 qualifying order
```

### Total Orders

**Definition.** The count of orders placed by the cohort's users, counting
only orders that fall within each user's own 90-day window.

**Formula.**

```
Total Orders = COUNT(DISTINCT order_id) for qualifying orders
```

### Total Gross Order Value

**Definition.** The sum of gross value across every qualifying order line —
the total economic value the cohort generated within its 90-day window.

**Formula.**

```
Total Gross Order Value = Σ gross_value, over all qualifying order lines
```

### gross_value (order-line field)

**Definition.** The most granular building block: what a single item sold
for, net of what it cost to fulfill. Revenue is the product's list price; cost
is the sum of that product's supply components.

**Formula.**

```
gross_value = revenue − cost
```

---

### Simulator metric: planning goal

When a user sets a growth target in CLUE's simulator, the target is expressed
as a percentage lift over the historical baseline for the cohort being
explained:

```
Goal Value = Baseline 90-Day Customer Value × (1 + Uplift % / 100)
```

CLUE treats the three multiplicative components above (conversion rate,
orders per purchasing customer, average order value) as adjustable
assumptions and propagates any change through the same identities used to
compute the historical metric, so a simulated scenario remains internally
consistent with how the real metric is defined.

### Month-over-month change

Every KPI card also reports how a metric moved relative to the prior
acquisition month in the data — not merely the prior month within the current
filter selection — using:

```
Change      = Current Month Value − Previous Month Value
Change (%)  = Change / |Previous Month Value|
```

No change is shown for the earliest cohort in the dataset, since there is no
prior month to compare against.

---

## Who this is for

CLUE is designed for two audiences:

- **Non-technical decision-makers**, who need to understand what is driving a
  metric and explore possible scenarios for moving it, without reading SQL.
- **Data professionals**, who inherit dashboards built by others and need a
  fast, reliable way to verify and explain how a metric is computed — down to
  the source data — before presenting it to stakeholders.
