"""
build.py
--------
Offline build: raw CSV -> the modeled data source the dashboard reads.

Run once from the baseline_dashboard directory:

    python -m datasource.build

This is the only code that ever touches the raw CSVs (~546 MB). Everything the
app does at runtime reads the Parquet written here. The modeled layer is also
exactly the depth `View Underlying Data` exposes -- rows and fields of the
dashboard's data source, not the upstream pipeline.

Outputs, in data/modeled/:
    customers.parquet             one row per acquired user
    customer_age_facts.parquet    one row per (purchasing user, age month)
    customer_window_facts.parquet one row per purchasing user, first 90 days
    orders.parquet              one row per order
    order_items.parquet         one row per order line
    products.parquet            per-sku economics
    SYNTHESIZED.md              what was generated and how
"""

from pathlib import Path

import pandas as pd

from datasource.age import (
    TIME_SHIFT_DAYS,
    apply_time_shift,
    customer_age_days,
    customer_age_month,
)
from datasource.synthesize import (
    CONVERSION_BASE,
    CONVERSION_SEASONAL_AMPLITUDE,
    CONVERSION_TREND_PER_YEAR,
    LAG_BUCKETS,
    build_non_purchasers,
    signup_lag_days,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data"
MODELED_DIR = RAW_DIR / "modeled"

# Age months retained in the month-grain aggregation table. The dashboard no
# longer slices by age month, but CLUE still reads this table, so it is still
# built.
MAX_AGE_MONTH = 12

# The dashboard's observation window, in days from each user's own acquisition
# date. Day 0 is the acquisition day, so the window is offsets 0..89.
WINDOW_DAYS = 90

CENTS = 100.0


def _log(message: str) -> None:
    print(message, flush=True)


# ---------------------------------------------------------------------------
# Product economics
# ---------------------------------------------------------------------------

def build_products() -> pd.DataFrame:
    """
    Per-sku revenue and cost in dollars.

    Revenue is the product's list price. Cost is the sum of its supply lines --
    raw_supplies holds several rows per sku, one per component. Their
    difference is `gross_value`, the field every value metric is built from.
    """
    products = pd.read_csv(RAW_DIR / "raw_products.csv")
    supplies = pd.read_csv(RAW_DIR / "raw_supplies.csv")

    cost = supplies.groupby("sku")["cost"].sum().rename("cost_cents")
    products = products.join(cost, on="sku")

    if products.cost_cents.isna().any():
        missing = products.loc[products.cost_cents.isna(), "sku"].tolist()
        raise ValueError(f"no supply rows for sku(s): {missing}")

    out = pd.DataFrame(
        {
            "product_id": products.sku,
            "product_name": products.name,
            "product_type": products.type,
            "revenue": (products.price / CENTS).round(2),
            "cost": (products.cost_cents / CENTS).round(2),
        }
    )
    out["gross_value"] = (out.revenue - out.cost).round(2)

    if (out.gross_value <= 0).any():
        raise ValueError("a product has non-positive gross value")

    return out


# ---------------------------------------------------------------------------
# Order items
# ---------------------------------------------------------------------------

def build_order_items(products: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Order lines priced out to revenue / cost / gross_value.

    Returns the line-level table and the per-order rollup. Orders carry their
    own revenue and cost so the order-level underlying-data view never has to
    join back into the three-million-row line table at click time.
    """
    items = pd.read_csv(
        RAW_DIR / "raw_order_items.csv",
        usecols=["id", "order_id", "sku"],
        dtype={"sku": "category"},
    )
    items = items.rename(columns={"id": "order_item_id", "sku": "product_id"})

    economics = products.set_index("product_id")
    for column in ("product_name", "revenue", "cost", "gross_value"):
        items[column] = (
            items.product_id.map(economics[column]).astype(economics[column].dtype)
        )

    if items.revenue.isna().any():
        raise ValueError("order items reference a sku missing from raw_products")

    per_order = (
        items.groupby("order_id", observed=True)[["revenue", "cost", "gross_value"]]
        .sum()
        .round(2)
    )
    return items, per_order


# ---------------------------------------------------------------------------
# Orders and customers
# ---------------------------------------------------------------------------

def build_orders(per_order: pd.DataFrame) -> pd.DataFrame:
    """Orders with shifted timestamps and their line rollup attached."""
    orders = pd.read_csv(
        RAW_DIR / "raw_orders.csv",
        usecols=["id", "customer", "ordered_at", "store_id"],
        parse_dates=["ordered_at"],
    )
    orders = orders.rename(columns={"id": "order_id", "customer": "user_id"})

    if orders.order_id.duplicated().any():
        raise ValueError("duplicate order ids in raw_orders")

    orders["ordered_at"] = apply_time_shift(orders.ordered_at)
    for column in ("revenue", "cost", "gross_value"):
        orders[column] = (
            orders.order_id.map(per_order[column]).fillna(0.0).round(2)
        )
    return orders


def first_complete_cohort_month(orders: pd.DataFrame) -> pd.Period:
    """
    The earliest acquisition month that is not left-censored.

    A purchaser's acquisition date is their first order less a signup lag, so a
    cohort month earlier than the first observed order can only ever contain
    purchasers whose lag was long enough to reach back that far. Those cohorts
    are not small samples -- they are biased samples, missing every fast
    converter by construction, and their 90-day conversion rate collapses
    toward zero for a reason that has nothing to do with the business.

    A cohort month is complete once a lag-0 purchaser in it would have been
    observable, which is the month of the first order in the data.
    """
    return orders.ordered_at.min().to_period("M")


def build_customers(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Acquired users: the real purchasers plus the synthesized non-purchasers.

    A purchaser's acquisition date is their first order less a signup lag, so
    the real cohort shape is preserved and simply shifted earlier. Cohort
    months too early to be complete are dropped -- see
    `first_complete_cohort_month`.
    """
    raw_customers = pd.read_csv(RAW_DIR / "raw_customers.csv", usecols=["id"])
    real_ids = set(raw_customers.id)

    orphans = set(orders.user_id) - real_ids
    if orphans:
        raise ValueError(f"{len(orphans)} orders reference unknown customers")

    first_order = orders.groupby("user_id")["ordered_at"].min().rename("first_order_at")
    purchasers = first_order.reset_index()

    lag = signup_lag_days(purchasers.user_id)
    purchasers["account_created_at"] = purchasers.first_order_at - pd.to_timedelta(
        lag, unit="D"
    )
    purchasers["is_purchaser"] = True

    complete_from = first_complete_cohort_month(orders)
    purchasers = purchasers[
        purchasers.account_created_at.dt.to_period("M") >= complete_from
    ].reset_index(drop=True)

    acquisition_months = purchasers.account_created_at.dt.to_period("M")
    non_purchasers = build_non_purchasers(acquisition_months, existing_ids=real_ids)
    non_purchasers["first_order_at"] = pd.NaT
    non_purchasers["is_purchaser"] = False

    customers = pd.concat([purchasers, non_purchasers], ignore_index=True)
    customers["acquisition_month"] = customers.account_created_at.dt.to_period(
        "M"
    ).astype(str)
    customers["account_created_at"] = customers.account_created_at.dt.floor("s")

    return customers[
        [
            "user_id",
            "account_created_at",
            "acquisition_month",
            "is_purchaser",
            "first_order_at",
        ]
    ].sort_values("user_id", ignore_index=True)


def attach_age(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Add customer_age_month to each order, relative to that user's acquisition."""
    acquired_at = customers.set_index("user_id").account_created_at
    orders = orders.copy()
    orders["acquisition_at"] = orders.user_id.map(acquired_at)
    orders["customer_age_month"] = customer_age_month(
        orders.ordered_at, orders.acquisition_at
    )
    orders["customer_age_day"] = customer_age_days(
        orders.ordered_at, orders.acquisition_at
    )

    if (orders.customer_age_month < 1).any():
        raise ValueError("an order precedes its customer's acquisition date")
    if (orders.customer_age_day < 0).any():
        raise ValueError("an order precedes its customer's acquisition date")

    return orders.drop(columns="acquisition_at")


def build_age_facts(orders: pd.DataFrame) -> pd.DataFrame:
    """
    The aggregation table every KPI and both charts are computed from.

    One row per (purchasing user, age month) for the first MAX_AGE_MONTH
    months -- a few tens of thousands of rows, so any reference period and
    observation window can be aggregated instantly.
    """
    window = orders[orders.customer_age_month <= MAX_AGE_MONTH]
    facts = (
        window.groupby(["user_id", "customer_age_month"], observed=True)
        .agg(orders=("order_id", "size"), gross_value=("gross_value", "sum"))
        .reset_index()
    )
    facts["gross_value"] = facts.gross_value.round(2)
    return facts.sort_values(["user_id", "customer_age_month"], ignore_index=True)


def build_window_facts(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Per-user totals over the first WINDOW_DAYS days -- the table every KPI is
    computed from.

    One row per user who ordered inside their own window, so it is a few
    thousand rows and any reference period aggregates instantly. Revenue and
    cost are carried alongside gross value because the dashboard reports all
    three.
    """
    window = orders[orders.customer_age_day.between(0, WINDOW_DAYS - 1)]
    facts = (
        window.groupby("user_id", observed=True)
        .agg(
            orders=("order_id", "size"),
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            gross_value=("gross_value", "sum"),
        )
        .reset_index()
    )
    for column in ("revenue", "cost", "gross_value"):
        facts[column] = facts[column].round(2)
    return facts.sort_values("user_id", ignore_index=True)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_cohorts(customers: pd.DataFrame) -> None:
    """
    Print acquisition volume by month and the best 3-month windows.

    The default reference period is chosen from this, not assumed: the time
    shift is not a whole number of months, so cohorts land a day or two off the
    calendar month line.
    """
    counts = (
        customers.groupby("acquisition_month")
        .agg(acquired=("user_id", "size"), purchasers=("is_purchaser", "sum"))
        .sort_index()
    )
    _log("\nAcquisition by month (acquired / purchasers):")
    for month, row in counts.iterrows():
        _log(f"  {month}  {row.acquired:6,d}  {row.purchasers:6,d}")

    rolling = counts.acquired.rolling(3).sum().dropna()
    _log("\nLargest 3-month acquisition windows:")
    for end_month, total in rolling.sort_values(ascending=False).head(5).items():
        start = pd.Period(end_month, freq="M") - 2
        _log(f"  {start} to {end_month}: {int(total):,} acquired users")


def write_synthesis_notes(
    customers: pd.DataFrame, window_facts: pd.DataFrame
) -> None:
    """Record what was generated, so the modeled data is never mistaken for raw."""
    purchasers = int(customers.is_purchaser.sum())
    total = len(customers)
    converted_in_window = int(len(window_facts))
    buckets = "\n".join(
        f"| {start}-{end} days | {weight:.2f} |" for start, end, weight in LAG_BUCKETS
    )

    beyond_window = sum(
        weight for start, _, weight in LAG_BUCKETS if start >= WINDOW_DAYS
    )
    base = CONVERSION_BASE
    trend = CONVERSION_TREND_PER_YEAR
    seasonal = CONVERSION_SEASONAL_AMPLITUDE
    window_days = WINDOW_DAYS

    (MODELED_DIR / "SYNTHESIZED.md").write_text(
        f"""# Synthesized fields

Generated by `datasource/build.py`. Everything here is deterministic -- values
derive from a stable hash of the customer id or cohort month, so every build
produces identical output.

## Time shift: +{TIME_SHIFT_DAYS} days

Every timestamp is moved forward by {TIME_SHIFT_DAYS} days (exactly
{TIME_SHIFT_DAYS // 7} weeks) so the data reads as current. The final order
moves from 2022-08-30 19:59 to 2026-06-30 19:59.

A whole number of weeks preserves each order's day of week, which matters for a
business with a strong weekly rhythm. Subtract {TIME_SHIFT_DAYS} days from any
timestamp to recover the original date.

## account_created_at

The raw data has no acquisition date, so signup is placed a lag before each
purchaser's first order:

| Lag | Probability |
|---|---:|
{buckets}

Uniform within each bucket. Cohort shape is inherited from the real first-order
distribution, shifted earlier.

## Incomplete cohort months

Acquisition months earlier than the first observed order are dropped. Signup is
derived by subtracting a lag from the first order, so those months could only
ever contain long-lag purchasers -- a biased sample missing every fast
converter, whose {window_days}-day conversion rate collapses toward zero for
reasons that have nothing to do with the business.

The tail matters: {beyond_window:.0%} of purchasers place their first order
after day {window_days}, which is what keeps the dashboard's {window_days}-day
observation window meaningful. With every purchaser converting inside it, the
window would exclude nothing and {window_days}-day conversion would be
identical to lifetime conversion.

## Non-purchasing acquired users

Every customer in the raw data has orders, so purchase conversion would be
exactly 100% for every cohort. Since the headline metric is value *per acquired
user*, users who never purchase have to exist for it to mean anything.

Signup-only users are generated per cohort month against a target conversion
rate. That rate is a *function of the month*, not an independent draw:

    conversion = {base:.2f}
               + {trend:+.2f}/year secular trend
               + {seasonal:.2f} annual seasonal term (peaking in November)
               + small deterministic jitter

An earlier version drew each month independently in a fixed range, which made a
per-cohort-month conversion chart pure noise -- there was no shape to read
because there was none to find.

- Real purchasers: {purchasers:,}
- Synthesized non-purchasers: {total - purchasers:,}
- Total acquired users: {total:,} ({purchasers / total:.1%} lifetime conversion)
- Purchasers converting within {window_days} days: {converted_in_window:,}
  ({converted_in_window / total:.1%} of acquired users)

## Not synthesized

Orders, order lines, product prices and supply costs are all real. `gross_value`
is computed from them as `revenue - cost`.
"""
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    MODELED_DIR.mkdir(parents=True, exist_ok=True)

    _log("Building product economics...")
    products = build_products()

    _log("Pricing order items...")
    order_items, per_order = build_order_items(products)

    _log("Loading orders...")
    orders = build_orders(per_order)

    _log("Deriving acquisition dates and non-purchasing users...")
    customers = build_customers(orders)

    # Purchasers in left-censored cohort months were dropped above; their orders
    # and order lines go with them, so nothing downstream references a user the
    # modeled data no longer has.
    acquired = set(customers.user_id)
    dropped_orders = int((~orders.user_id.isin(acquired)).sum())
    if dropped_orders:
        orders = orders[orders.user_id.isin(acquired)].reset_index(drop=True)
        order_items = order_items[
            order_items.order_id.isin(set(orders.order_id))
        ].reset_index(drop=True)
        _log(
            f"  dropped {dropped_orders:,} orders from incomplete cohort months "
            f"(before {first_complete_cohort_month(orders)})"
        )

    _log("Attaching customer age...")
    orders = attach_age(orders, customers)

    _log("Aggregating age facts...")
    age_facts = build_age_facts(orders)

    _log(f"Aggregating {WINDOW_DAYS}-day window facts...")
    window_facts = build_window_facts(orders)

    _log("Writing parquet...")
    products.to_parquet(MODELED_DIR / "products.parquet", index=False)
    order_items.to_parquet(MODELED_DIR / "order_items.parquet", index=False)
    orders.to_parquet(MODELED_DIR / "orders.parquet", index=False)
    customers.to_parquet(MODELED_DIR / "customers.parquet", index=False)
    age_facts.to_parquet(MODELED_DIR / "customer_age_facts.parquet", index=False)
    window_facts.to_parquet(
        MODELED_DIR / "customer_window_facts.parquet", index=False
    )
    write_synthesis_notes(customers, window_facts)

    _log("\nRow counts:")
    for name, frame in (
        ("products", products),
        ("order_items", order_items),
        ("orders", orders),
        ("customers", customers),
        ("customer_age_facts", age_facts),
        ("customer_window_facts", window_facts),
    ):
        _log(f"  {name:<20} {len(frame):>10,d}")

    _log(
        f"\nOrders span {orders.ordered_at.min()} to {orders.ordered_at.max()}"
        f"\nPurchasers {int(customers.is_purchaser.sum()):,} of "
        f"{len(customers):,} acquired "
        f"({customers.is_purchaser.mean():.1%} conversion)"
    )
    report_cohorts(customers)


if __name__ == "__main__":
    main()
