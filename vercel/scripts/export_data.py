"""Export baseline_dashboard/data/modeled parquet to vercel/public/data/*.json. Run from repo root: .venv/bin/python vercel/scripts/export_data.py"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "baseline_dashboard"

# Reuse the dashboard's own aggregation (metrics/compute.py; imports only pandas).
sys.path.insert(0, str(DASHBOARD))
from metrics.compute import WINDOW_DAYS, month_table  # noqa: E402

DEFAULT_MODELED_DIR = DASHBOARD / "data" / "modeled"
DEFAULT_OUT_DIR = ROOT / "vercel" / "public" / "data"


def _log(message: str) -> None:
    print(message, flush=True)


def load_tables(modeled: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reads customers, window facts and in-window orders (datasource/loader.py)."""
    missing = [
        name
        for name in ("customers", "customer_window_facts", "orders")
        if not (modeled / f"{name}.parquet").exists()
    ]
    if missing:
        raise SystemExit(
            f"Modeled data source not found in {modeled} (missing: "
            f"{', '.join(missing)}).\nBuild it first:\n"
            f"  cd baseline_dashboard && ../.venv/bin/python -m datasource.build"
        )

    customers = pd.read_parquet(
        modeled / "customers.parquet",
        columns=["user_id", "account_created_at", "acquisition_month"],
    )
    customers["acquisition_month"] = pd.PeriodIndex(
        customers.acquisition_month, freq="M"
    )
    window_facts = pd.read_parquet(
        modeled / "customer_window_facts.parquet",
        columns=["user_id", "orders", "gross_value"],
    )
    orders = pd.read_parquet(
        modeled / "orders.parquet",
        columns=["order_id", "user_id", "revenue", "cost", "gross_value",
                 "customer_age_day"],
    )
    # Keep orders in each user's first 90 days (load_orders).
    orders = orders[orders.customer_age_day.between(0, WINDOW_DAYS - 1)]
    return customers, window_facts, orders


def cohort_rows(customers: pd.DataFrame, window_facts: pd.DataFrame) -> list[dict]:
    """Four counts per acquisition month, from metrics/compute.py · month_table()."""
    table = month_table(customers, window_facts)
    rows = []
    for row in table.itertuples(index=False):
        rows.append(
            {
                "month": str(row.acquisition_month),
                "acquired_users": int(row.acquired_users),
                "purchasing_customers": int(row.purchasing_customers),
                "total_orders": int(row.total_orders),
                # Round to cents.
                "total_gross_order_value": round(
                    float(row.total_gross_order_value), 2
                ),
            }
        )
    return rows


def _columnar(frame: pd.DataFrame) -> dict:
    """{columns, rows} layout, smaller than a list of records."""
    return {
        "columns": list(frame.columns),
        "rows": frame.astype(object).where(frame.notna(), None).values.tolist(),
    }


def month_files(
    customers: pd.DataFrame, window_facts: pd.DataFrame, orders: pd.DataFrame
):
    """Yields (month, rows) per month; columns as in components/underlying_data.py."""
    totals = window_facts.set_index("user_id")
    acquired_at = customers.set_index("user_id").account_created_at

    for month, group in customers.groupby("acquisition_month", sort=True):
        users = pd.DataFrame(
            {
                "user_id": group.user_id.values,
                "acquisition_date": group.account_created_at.dt.strftime(
                    "%Y-%m-%d"
                ).values,
            }
        )
        users[f"orders_{WINDOW_DAYS}d"] = (
            users.user_id.map(totals.orders).fillna(0).astype(int)
        )
        users[f"gross_value_{WINDOW_DAYS}d"] = (
            users.user_id.map(totals.gross_value).fillna(0.0).round(2)
        )
        users.insert(
            2,
            f"purchasing_customer_{WINDOW_DAYS}d",
            (users[f"orders_{WINDOW_DAYS}d"] > 0).astype(int),
        )
        users = users.sort_values(
            ["acquisition_date", "user_id"], ignore_index=True
        )

        mine = orders[orders.user_id.isin(set(group.user_id))]
        order_rows = pd.DataFrame(
            {
                "order_id": mine.order_id.values,
                "user_id": mine.user_id.values,
                "acquisition_date": mine.user_id.map(acquired_at)
                .dt.strftime("%Y-%m-%d")
                .values,
                "days_since_acquisition": mine.customer_age_day.astype(int).values,
                "revenue": mine.revenue.round(2).values,
                "cost": mine.cost.round(2).values,
                "gross_value": mine.gross_value.round(2).values,
            }
        ).sort_values(["user_id", "days_since_acquisition"], ignore_index=True)

        yield str(month), {
            "month": str(month),
            "customers": _columnar(users),
            "orders": _columnar(order_rows),
        }


def _write_json(path: Path, payload: dict) -> int:
    text = json.dumps(payload, separators=(",", ":"))
    path.write_text(text)
    return len(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--modeled-dir", type=Path, default=DEFAULT_MODELED_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    _log(f"Reading {args.modeled_dir}")
    customers, window_facts, orders = load_tables(args.modeled_dir)

    months_dir = args.out / "months"
    months_dir.mkdir(parents=True, exist_ok=True)
    # Remove month files left over from a previous export.
    for stale in months_dir.glob("*.json"):
        stale.unlink()

    cohorts = cohort_rows(customers, window_facts)
    size = _write_json(
        args.out / "cohorts.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "window_days": WINDOW_DAYS,
            "months": cohorts,
        },
    )
    _log(f"  cohorts.json            {len(cohorts):>4} months   {size / 1024:8.1f} KB")

    total = 0
    for month, payload in month_files(customers, window_facts, orders):
        total += _write_json(months_dir / f"{month}.json", payload)
    _log(f"  months/*.json           {len(cohorts):>4} files    {total / 1024:8.1f} KB")
    _log(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
