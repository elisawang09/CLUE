"""
loader.py
---------
Cached readers for the modeled data source.

`@st.cache_data` parses each Parquet once per server process and shares it
across reruns and sessions, so interacting with a filter never re-reads from
disk. The two small tables are loaded eagerly by the dashboard; the two
million-row tables are loaded only when a participant opens the order-level
underlying-data view.
"""

import pandas as pd
import streamlit as st

from datasource.schema import TABLES, require_built, validate


@st.cache_data(show_spinner=False)
def _read(name: str, columns: tuple[str, ...] | None = None) -> pd.DataFrame:
    require_built()
    frame = pd.read_parquet(
        TABLES[name].path, columns=list(columns) if columns else None
    )
    return validate(name, frame) if columns is None else frame


@st.cache_data(show_spinner=False)
def load_customers() -> pd.DataFrame:
    """Acquired users, with acquisition_month as a period for range filtering."""
    customers = _read("customers")
    customers = customers.copy()
    customers["acquisition_month"] = pd.PeriodIndex(
        customers.acquisition_month, freq="M"
    )
    return customers


@st.cache_data(show_spinner=False)
def load_age_facts() -> pd.DataFrame:
    """Per-user, per-age-month orders and gross value."""
    return _read("customer_age_facts")


@st.cache_data(show_spinner=False)
def load_products() -> pd.DataFrame:
    return _read("products")


@st.cache_data(show_spinner=False)
def load_orders(user_ids: tuple[str, ...], max_age_month: int) -> pd.DataFrame:
    """
    Orders for a specific set of users, within their first `max_age_month`
    months.

    Keyed on the user set so each distinct drilldown is cached separately.
    Reads the 2M-row table, so it is only called from the underlying-data view.
    """
    orders = _read(
        "orders",
        columns=("order_id", "user_id", "ordered_at", "revenue", "cost",
                 "gross_value", "customer_age_month"),
    )
    return orders[
        orders.user_id.isin(set(user_ids))
        & orders.customer_age_month.between(1, max_age_month)
    ].copy()


@st.cache_data(show_spinner=False)
def load_order_items(order_ids: tuple[str, ...]) -> pd.DataFrame:
    """Order lines for specific orders. Reads the 3M-row table."""
    items = _read(
        "order_items",
        columns=("order_item_id", "order_id", "product_id", "product_name",
                 "revenue", "cost", "gross_value"),
    )
    return items[items.order_id.isin(set(order_ids))].copy()


def available_months() -> pd.PeriodIndex:
    """Every month in which at least one user was acquired, ascending."""
    months = load_customers().acquisition_month.unique()
    return pd.PeriodIndex(sorted(months), freq="M")
