"""Tests for the deterministic synthesis of signup lag and non-purchasing users."""

import unittest

import numpy as np
import pandas as pd

from datasource.synthesize import (
    CONVERSION_BOUNDS,
    CONVERSION_EPOCH,
    CONVERSION_SEASONAL_PEAK_MONTH,
    CONVERSION_TREND_PER_YEAR,
    LAG_BUCKETS,
    build_non_purchasers,
    conversion_rate_by_month,
    signup_lag_days,
)


def fake_ids(n: int, prefix: str = "cust") -> pd.Series:
    return pd.Series([f"{prefix}-{i:06d}" for i in range(n)])


class TestSignupLag(unittest.TestCase):
    def setUp(self):
        self.ids = fake_ids(20_000)
        self.lag = signup_lag_days(self.ids)

    def test_bucket_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(w for _, _, w in LAG_BUCKETS), 1.0)

    def test_the_tail_reaches_past_the_observation_window(self):
        """
        Without purchasers converting after day 90, the dashboard's 90-day
        window excludes nobody and its conversion rate is just lifetime
        conversion under another name.
        """
        from metrics.compute import WINDOW_DAYS

        beyond = sum(
            weight for start, _, weight in LAG_BUCKETS if start >= WINDOW_DAYS
        )
        self.assertGreater(beyond, 0.05)
        self.assertLess(beyond, 0.35)

    def test_lag_stays_inside_the_declared_range(self):
        self.assertGreaterEqual(self.lag.min(), LAG_BUCKETS[0][0])
        self.assertLessEqual(self.lag.max(), LAG_BUCKETS[-1][1])

    def test_bucket_proportions_match_the_weights(self):
        for start, end, weight in LAG_BUCKETS:
            share = ((self.lag >= start) & (self.lag <= end)).mean()
            self.assertAlmostEqual(
                share, weight, delta=0.015,
                msg=f"bucket {start}-{end} got {share:.3f}, expected {weight}",
            )

    def test_every_day_in_a_bucket_is_reachable(self):
        # Guards against an off-by-one that would strand a bucket's last day.
        expected: set[int] = set()
        for start, end, _ in LAG_BUCKETS:
            expected |= set(range(start, end + 1))
        self.assertEqual(set(self.lag.unique()), expected)

    def test_deterministic_across_calls(self):
        pd.testing.assert_series_equal(self.lag, signup_lag_days(self.ids))

    def test_independent_of_row_order(self):
        shuffled = self.ids.sample(frac=1, random_state=0)
        again = signup_lag_days(shuffled)
        pd.testing.assert_series_equal(
            self.lag.sort_index(), again.sort_index()
        )

    def test_preserves_the_index(self):
        ids = pd.Series(["a", "b", "c"], index=[10, 20, 30])
        self.assertEqual(list(signup_lag_days(ids).index), [10, 20, 30])


class TestConversionRates(unittest.TestCase):
    """
    Conversion is a function of the cohort month, not an independent draw.

    An earlier version drew each month independently in a fixed range, which
    made the per-cohort-month conversion chart pure noise -- there was no shape
    to read because there was none to find. These tests pin the shape.
    """

    def test_rates_stay_inside_the_declared_bounds(self):
        months = pd.period_range("2019-10", "2026-12", freq="M")
        rates = conversion_rate_by_month(months)
        low, high = CONVERSION_BOUNDS
        self.assertGreaterEqual(rates.min(), low)
        self.assertLessEqual(rates.max(), high)

    def test_rates_actually_vary(self):
        months = pd.period_range("2020-07", "2024-07", freq="M")
        rates = conversion_rate_by_month(months)
        self.assertGreater(rates.std(), 0.01)

    def test_the_trend_points_the_declared_way(self):
        """Five years apart, the level has moved by roughly the stated trend."""
        early = conversion_rate_by_month(
            pd.period_range("2020-07", "2021-06", freq="M")
        ).mean()
        late = conversion_rate_by_month(
            pd.period_range("2023-07", "2024-06", freq="M")
        ).mean()
        self.assertAlmostEqual(late - early, 3 * CONVERSION_TREND_PER_YEAR,
                               delta=0.015)

    def test_the_seasonal_term_peaks_where_it_says_it_does(self):
        """
        Detrended and averaged over enough years, the peak calendar month is
        the declared one.

        The trend has to come out first: it falls monotonically through each
        year, which biases January over November by about as much as the
        seasonal term separates them. Averaging the raw rates by calendar month
        would therefore report the wrong peak while the seasonal term was
        perfectly correct.
        """
        months = pd.period_range("2020-01", "2027-12", freq="M")
        rates = conversion_rate_by_month(months)
        trend = pd.Series(
            [
                CONVERSION_TREND_PER_YEAR * (month - CONVERSION_EPOCH).n / 12.0
                for month in months
            ],
            index=rates.index,
        )
        detrended = rates - trend
        by_calendar_month = detrended.groupby(
            [month.month for month in months]
        ).mean()
        self.assertEqual(
            int(by_calendar_month.idxmax()), CONVERSION_SEASONAL_PEAK_MONTH
        )

    def test_neighbouring_months_move_together(self):
        """
        Structure, not noise: consecutive months are close, which an
        independent uniform draw over the same span would not be.
        """
        months = pd.period_range("2020-07", "2024-07", freq="M")
        rates = conversion_rate_by_month(months)
        self.assertLess(rates.diff().abs().mean(), 0.02)

    def test_deterministic(self):
        months = pd.period_range("2022-01", "2022-06", freq="M")
        pd.testing.assert_series_equal(
            conversion_rate_by_month(months), conversion_rate_by_month(months)
        )


class TestNonPurchasers(unittest.TestCase):
    def setUp(self):
        months = pd.period_range("2022-01", "2022-12", freq="M")
        self.acquisition_months = pd.Series(
            np.repeat(months, 100)  # 100 purchasers per month
        )
        self.non_purchasers = build_non_purchasers(
            self.acquisition_months, existing_ids=set()
        )

    def test_counts_follow_the_conversion_rate(self):
        rates = conversion_rate_by_month(
            self.acquisition_months.value_counts().sort_index().index
        )
        created = pd.Series(
            self.non_purchasers.account_created_at.dt.to_period("M")
        ).value_counts()
        for month, rate in rates.items():
            expected = int(round(100 / rate)) - 100
            self.assertEqual(created[month], expected, msg=f"month {month}")

    def test_overall_conversion_lands_near_forty_percent(self):
        purchasers = len(self.acquisition_months)
        acquired = purchasers + len(self.non_purchasers)
        self.assertAlmostEqual(purchasers / acquired, 0.42, delta=0.06)

    def test_ids_are_unique(self):
        self.assertEqual(
            len(self.non_purchasers.user_id.unique()), len(self.non_purchasers)
        )

    def test_created_dates_fall_inside_their_cohort_month(self):
        # build_non_purchasers assigns each user to a month; verify none drifted.
        counts = self.acquisition_months.value_counts().sort_index()
        months = set(counts.index)
        created_months = set(self.non_purchasers.account_created_at.dt.to_period("M"))
        self.assertTrue(created_months.issubset(months))

    def test_collision_with_a_real_id_is_an_error(self):
        planted = self.non_purchasers.user_id.iloc[0]
        with self.assertRaises(ValueError):
            build_non_purchasers(self.acquisition_months, existing_ids={planted})

    def test_deterministic(self):
        again = build_non_purchasers(self.acquisition_months, existing_ids=set())
        pd.testing.assert_frame_equal(self.non_purchasers, again)

    def test_empty_input_gives_empty_output(self):
        empty = build_non_purchasers(
            pd.Series([], dtype="period[M]"), existing_ids=set()
        )
        self.assertEqual(len(empty), 0)
        self.assertEqual(list(empty.columns), ["user_id", "account_created_at"])


if __name__ == "__main__":
    unittest.main()
