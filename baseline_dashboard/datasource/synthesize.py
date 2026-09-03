"""
synthesize.py
-------------
The two fields the raw dataset cannot supply.

Everything here is deterministic: values derive from a stable hash of the
customer id (or cohort month), never from a global RNG or row order, so the
build produces identical output on every machine and every run. That matters
because study participants must all see the same numbers.

1. `account_created_at` -- the raw data has no acquisition date, so signup is
   placed a short lag before each customer's first order.

2. Non-purchasing acquired users -- every customer in the raw data has orders,
   so purchase conversion would be exactly 100% for every cohort, flattening a
   KPI card and collapsing the headline metric to Orders x AOV. "Value per
   acquired user" only means something when some acquired users never buy.
"""

import hashlib

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Signup lag
# ---------------------------------------------------------------------------
#
# Lag from account creation to first order. Most customers buy within a month
# of signing up, and the tail thins out -- but it has to reach past day 90.
#
# An earlier version capped the lag at 59 days, which made the dashboard's
# 90-day observation window inert: every purchaser converted inside it, so
# 90-day conversion was identical to lifetime conversion and the window did no
# work at all. The last two buckets are what give the window something to
# exclude; together they place 15% of purchasers beyond day 90.

LAG_BUCKETS: tuple[tuple[int, int, float], ...] = (
    (0, 14, 0.24),
    (15, 29, 0.22),
    (30, 44, 0.17),
    (45, 59, 0.12),
    (60, 89, 0.10),
    (90, 149, 0.09),
    (150, 269, 0.06),
)

# ---------------------------------------------------------------------------
# Purchase conversion by cohort month
# ---------------------------------------------------------------------------
#
# Conversion is a *function of the cohort month*, not an independent draw per
# month. Drawing each month independently (as an earlier version did) produced
# a chart of pure noise: with one bar per acquisition month there was no shape
# to read, because there was none to find. The terms below are the shape.
#
# Level, then a gentle secular decline, then an annual seasonal term, then a
# small deterministic jitter so the curve is not implausibly smooth. All of it
# is keyed off the month itself, so the build stays reproducible.

CONVERSION_BASE = 0.46            # roughly where the earliest cohorts sit
CONVERSION_TREND_PER_YEAR = -0.02  # slow decline across the ~5 years of data
CONVERSION_SEASONAL_AMPLITUDE = 0.03
CONVERSION_SEASONAL_PEAK_MONTH = 11  # November, ahead of the holiday season
CONVERSION_JITTER = 0.024          # peak-to-peak, centred on zero

# Cohort months are dated from the first month in the data, so the trend term
# does not depend on which slice of months a build happens to produce.
CONVERSION_EPOCH = pd.Period("2019-10", freq="M")

# Conversion is clamped into this range, so no combination of terms can produce
# a nonsensical rate at the ends of a longer-than-expected series.
CONVERSION_BOUNDS: tuple[float, float] = (0.20, 0.60)


def _uniforms(keys: pd.Series | list[str], salt: str, count: int = 1) -> np.ndarray:
    """
    Deterministic uniforms in [0, 1) -- shape (len(keys), count).

    Uses blake2b rather than Python's hash(), which is salted per process and
    would give different results on every run.
    """
    draws = np.empty((len(keys), count), dtype=np.float64)
    for row, key in enumerate(keys):
        digest = hashlib.blake2b(
            f"{salt}:{key}".encode(), digest_size=8 * count
        ).digest()
        for col in range(count):
            chunk = digest[col * 8 : (col + 1) * 8]
            draws[row, col] = int.from_bytes(chunk, "big") / 2**64
    return draws


def signup_lag_days(customer_ids: pd.Series) -> pd.Series:
    """
    Days between account creation and first order, one per customer.

    The bucket is chosen from the weights in LAG_BUCKETS and the day is drawn
    uniformly inside it.
    """
    draws = _uniforms(customer_ids, salt="signup-lag", count=2)
    bucket_draw, day_draw = draws[:, 0], draws[:, 1]

    edges = np.cumsum([weight for _, _, weight in LAG_BUCKETS])
    if not np.isclose(edges[-1], 1.0):
        raise ValueError(f"LAG_BUCKETS weights must sum to 1, got {edges[-1]}")

    lag = np.empty(len(customer_ids), dtype=np.int64)
    lower = 0.0
    for (start, end, _), upper in zip(LAG_BUCKETS, edges):
        in_bucket = (bucket_draw >= lower) & (bucket_draw < upper)
        span = end - start + 1
        lag[in_bucket] = start + np.floor(day_draw[in_bucket] * span).astype(np.int64)
        lower = upper

    return pd.Series(lag, index=customer_ids.index, name="signup_lag_days")


def conversion_rate_by_month(months: pd.Index) -> pd.Series:
    """
    Purchase conversion rate for each cohort month.

    Deterministic and structured: level + trend + seasonality + small jitter.
    This is *lifetime* conversion -- the share of the cohort that ever orders.
    The dashboard's 90-day rate is a fraction of it, because the widened
    LAG_BUCKETS leave some purchasers converting after day 90.
    """
    elapsed_months = np.array(
        [(pd.Period(month, freq="M") - CONVERSION_EPOCH).n for month in months],
        dtype=np.float64,
    )
    trend = CONVERSION_TREND_PER_YEAR * elapsed_months / 12.0

    calendar_month = np.array([pd.Period(month, freq="M").month for month in months])
    # Cosine, not sine: cosine is at its maximum where its argument is zero,
    # which puts the peak on CONVERSION_SEASONAL_PEAK_MONTH itself. A sine
    # would peak a quarter of a year later than the constant claims.
    seasonal = CONVERSION_SEASONAL_AMPLITUDE * np.cos(
        2 * np.pi * (calendar_month - CONVERSION_SEASONAL_PEAK_MONTH) / 12.0
    )

    draws = _uniforms([str(month) for month in months], salt="conversion-rate")[:, 0]
    jitter = (draws - 0.5) * CONVERSION_JITTER

    rates = CONVERSION_BASE + trend + seasonal + jitter
    low, high = CONVERSION_BOUNDS
    return pd.Series(
        np.clip(rates, low, high), index=months, name="conversion_rate"
    )


def _synthetic_user_id(month: str, index: int) -> str:
    """A UUID-shaped id for a synthesized user, stable across runs."""
    digest = hashlib.blake2b(
        f"non-purchaser:{month}:{index}".encode(), digest_size=16
    ).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"
    )


def build_non_purchasers(
    purchaser_acquisition_months: pd.Series,
    existing_ids: set[str],
) -> pd.DataFrame:
    """
    Generate acquired-but-never-purchased users.

    For each cohort month, a conversion rate implies how many acquired users
    the observed purchasers represent; the shortfall is created here. Their
    `account_created_at` is spread deterministically across the month, so
    cohort sizes stay smooth.

    Returns columns: user_id, account_created_at.
    """
    counts = purchaser_acquisition_months.value_counts().sort_index()
    rates = conversion_rate_by_month(counts.index)

    rows: list[dict[str, object]] = []
    for month, purchasers in counts.items():
        acquired = int(round(purchasers / rates[month]))
        shortfall = acquired - int(purchasers)
        if shortfall <= 0:
            continue

        month_start = month.to_timestamp()
        seconds_in_month = int(
            (month.to_timestamp(how="end") - month_start).total_seconds()
        )
        offsets = _uniforms(
            [f"{month}:{i}" for i in range(shortfall)], salt="non-purchaser-created"
        )[:, 0]

        for i in range(shortfall):
            user_id = _synthetic_user_id(str(month), i)
            if user_id in existing_ids:
                raise ValueError(f"synthetic id collided with a real one: {user_id}")
            rows.append(
                {
                    "user_id": user_id,
                    "account_created_at": month_start
                    + pd.Timedelta(seconds=int(offsets[i] * seconds_in_month)),
                }
            )

    return pd.DataFrame(rows, columns=["user_id", "account_created_at"])
