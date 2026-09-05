"""
schema.py
---------
Expected shape of each modeled table, and validation with readable errors.

The app is run by researchers during study sessions, so a stale or half-built
data directory has to fail with a sentence telling them what to do, not a
pandas KeyError three frames deep.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MODELED_DIR = Path(__file__).resolve().parent.parent / "data" / "modeled"

BUILD_HINT = (
    "Run `python -m datasource.build` from the baseline_dashboard directory "
    "to (re)build the modeled data source."
)


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    description: str

    @property
    def path(self) -> Path:
        return MODELED_DIR / f"{self.name}.parquet"


TABLES: dict[str, TableSpec] = {
    spec.name: spec
    for spec in (
        TableSpec(
            "customers",
            ("user_id", "account_created_at", "acquisition_month", "is_purchaser",
             "first_order_at"),
            "One row per acquired user.",
        ),
        TableSpec(
            "customer_window_facts",
            ("user_id", "orders", "revenue", "cost", "gross_value"),
            "One row per user who ordered within their own first 90 days.",
        ),
        TableSpec(
            "orders",
            ("order_id", "user_id", "ordered_at", "store_id", "revenue", "cost",
             "gross_value", "customer_age_month", "customer_age_day"),
            "One row per order.",
        ),
        TableSpec(
            "order_items",
            ("order_item_id", "order_id", "product_id", "product_name", "revenue",
             "cost", "gross_value"),
            "One row per order line.",
        ),
        TableSpec(
            "products",
            ("product_id", "product_name", "product_type", "revenue", "cost",
             "gross_value"),
            "Per-product revenue and cost.",
        ),
    )
}


class DataSourceError(RuntimeError):
    """Raised when the modeled data source is missing or malformed."""


def require_built() -> None:
    """Fail early and clearly if the build has not been run."""
    missing = [spec.name for spec in TABLES.values() if not spec.path.exists()]
    if missing:
        raise DataSourceError(
            f"Modeled data source is incomplete -- missing: {', '.join(sorted(missing))}.\n"
            f"{BUILD_HINT}"
        )


def validate(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Check a loaded table against its spec, returning it unchanged if valid."""
    spec = TABLES[name]

    missing = [column for column in spec.columns if column not in frame.columns]
    if missing:
        raise DataSourceError(
            f"`{name}` is missing column(s): {', '.join(missing)}.\n"
            f"Found: {', '.join(frame.columns)}.\n{BUILD_HINT}"
        )

    if frame.empty:
        raise DataSourceError(f"`{name}` has no rows.\n{BUILD_HINT}")

    return frame
