"""
age.py
------
Time-shift constant and the two customer-age derivations.

`customer_age_month` is anniversary-based, not calendar-based: month k covers
[acquisition + (k-1) months, acquisition + k months). A user acquired Dec 10 is
observed from Dec 10; one acquired Feb 15 is observed from Feb 15. This is what
lets every user in a reference period get an equal-length observation window.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Time shift
# ---------------------------------------------------------------------------
#
# Every timestamp in the modeled data source is moved forward by this offset so
# the dashboard reads as current. 1400 days lands the final order on
# 2026-06-30 19:59 and is exactly 200 weeks, so each order keeps its day of
# week -- this dataset has a strong weekly rhythm that a non-week-aligned shift
# would smear. Subtract the offset to recover the original dates.

TIME_SHIFT_DAYS = 1400
TIME_SHIFT = pd.Timedelta(days=TIME_SHIFT_DAYS)


def apply_time_shift(values: pd.Series) -> pd.Series:
    """Move a datetime series forward by the global time shift."""
    return values + TIME_SHIFT


def remove_time_shift(values: pd.Series) -> pd.Series:
    """Recover original dates from shifted ones."""
    return values - TIME_SHIFT


# ---------------------------------------------------------------------------
# Customer age in months
# ---------------------------------------------------------------------------

def customer_age_month(
    order_at: pd.Series,
    acquired_at: pd.Series,
) -> pd.Series:
    """
    Return the 1-based month index of each order relative to its customer's
    acquisition date.

    Month 1 is [acquired_at, acquired_at + 1 month), month 2 the next, and so
    on. An order placed before acquisition yields an index <= 0, which callers
    are expected to filter out rather than silently keep.

    Whole elapsed months are counted by calendar arithmetic, then decremented
    when the order's day-of-month has not yet reached the acquisition
    day-of-month -- i.e. when the final month is still in progress.

    Boundaries are date-granular: the index advances at midnight on the
    anniversary day, not at the acquisition time of day. Cohort analysis
    conventionally works in whole days, and the dashboard only ever buckets by
    month, so sub-day precision would add edge cases without changing a number.
    """
    order_at = pd.to_datetime(order_at)
    acquired_at = pd.to_datetime(acquired_at)

    months = (order_at.dt.year - acquired_at.dt.year) * 12 + (
        order_at.dt.month - acquired_at.dt.month
    )

    # The current month is only complete once the anniversary day is reached.
    # Clamp the acquisition day to the order month's length so an acquisition
    # on the 31st still rolls over in a shorter month. This makes the month
    # boundaries exactly `acquired_at + DateOffset(months=k)`, which clamps the
    # same way: a customer acquired Jan 31 starts month 2 on Feb 28.
    days_in_order_month = order_at.dt.days_in_month
    effective_acq_day = np.minimum(acquired_at.dt.day, days_in_order_month)
    incomplete = order_at.dt.day < effective_acq_day

    return (months - incomplete.astype(int) + 1).astype("int64")


# ---------------------------------------------------------------------------
# Customer age in days
# ---------------------------------------------------------------------------
#
# The dashboard's observation window is 90 days, which no month-based index can
# express -- 90 days is not three anniversary months. This is the derivation
# every windowed metric is filtered on.

def customer_age_days(
    order_at: pd.Series,
    acquired_at: pd.Series,
) -> pd.Series:
    """
    Return the 0-based day offset of each order from its customer's acquisition.

    Day 0 is the acquisition day itself, so the first 90 days are offsets
    0..89. An order placed before acquisition yields a negative offset, which
    callers are expected to filter out rather than silently keep.

    Date-granular, like `customer_age_month`: both boundaries fall at midnight
    rather than at the acquisition time of day. A customer acquired at 23:50
    would otherwise get a 90-day window almost a day shorter than one acquired
    at 00:10, which is not a distinction cohort analysis makes.
    """
    order_at = pd.to_datetime(order_at)
    acquired_at = pd.to_datetime(acquired_at)
    return (
        order_at.dt.normalize() - acquired_at.dt.normalize()
    ).dt.days.astype("int64")
