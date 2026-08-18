"""Tests for the time shift and the customer_age_month derivation."""

import unittest

import numpy as np
import pandas as pd

from datasource.age import (
    TIME_SHIFT_DAYS,
    apply_time_shift,
    customer_age_month,
    remove_time_shift,
)


def age(order: str, acquired: str) -> int:
    """Age month for a single (order, acquisition) pair."""
    return int(
        customer_age_month(
            pd.Series([pd.Timestamp(order)]),
            pd.Series([pd.Timestamp(acquired)]),
        ).iloc[0]
    )


class TestCustomerAgeMonth(unittest.TestCase):
    def test_acquisition_day_is_month_one(self):
        self.assertEqual(age("2022-12-10", "2022-12-10"), 1)

    def test_month_one_runs_up_to_the_anniversary(self):
        self.assertEqual(age("2022-12-31", "2022-12-10"), 1)
        self.assertEqual(age("2023-01-09", "2022-12-10"), 1)
        self.assertEqual(age("2023-01-10", "2022-12-10"), 2)

    def test_sixth_month_ends_the_day_before_the_six_month_anniversary(self):
        # Dec 10 + 6 months = Jun 10, so month 6 is [May 10, Jun 10).
        self.assertEqual(age("2023-05-10", "2022-12-10"), 6)
        self.assertEqual(age("2023-06-09", "2022-12-10"), 6)
        self.assertEqual(age("2023-06-10", "2022-12-10"), 7)

    def test_end_of_month_acquisition_clamps(self):
        # Jan 31 + 1 month clamps to Feb 28, which starts month 2.
        self.assertEqual(age("2023-02-27", "2023-01-31"), 1)
        self.assertEqual(age("2023-02-28", "2023-01-31"), 2)
        self.assertEqual(age("2023-03-30", "2023-01-31"), 2)
        self.assertEqual(age("2023-03-31", "2023-01-31"), 3)

    def test_leap_day(self):
        self.assertEqual(age("2024-02-29", "2024-02-29"), 1)
        self.assertEqual(age("2024-03-28", "2024-02-29"), 1)
        self.assertEqual(age("2024-03-29", "2024-02-29"), 2)
        # Acquired Jan 31 of a leap year: Feb 29 exists, so it starts month 2.
        self.assertEqual(age("2024-02-29", "2024-01-31"), 2)

    def test_orders_before_acquisition_are_not_positive(self):
        self.assertLessEqual(age("2022-12-09", "2022-12-10"), 0)

    def test_time_of_day_does_not_shift_the_boundary(self):
        self.assertEqual(age("2023-01-09 23:59:59", "2022-12-10 08:00:00"), 1)
        self.assertEqual(age("2023-01-10 00:00:01", "2022-12-10 08:00:00"), 2)

    def test_matches_dateoffset_boundaries(self):
        """
        The whole convention in one property: month k must be exactly
        [acq + (k-1) months, acq + k months), using pandas' own month
        arithmetic, which clamps end-of-month the same way we do.

        Checked over every acquisition date across two years (including a leap
        year) for the first 12 months, at both ends of each month.
        """
        acquisitions = pd.date_range("2023-01-01", "2024-12-31", freq="D")

        acq, expected, first_day, last_day = [], [], [], []
        for k in range(1, 13):
            starts = acquisitions + pd.DateOffset(months=k - 1)
            ends = acquisitions + pd.DateOffset(months=k)
            acq.append(acquisitions)
            expected.append(pd.Series(k, index=range(len(acquisitions))))
            first_day.append(starts)
            last_day.append(ends - pd.Timedelta(days=1))

        acq = pd.Series(pd.DatetimeIndex(np.concatenate(acq)))
        expected = pd.concat(expected, ignore_index=True)
        first_day = pd.Series(pd.DatetimeIndex(np.concatenate(first_day)))
        last_day = pd.Series(pd.DatetimeIndex(np.concatenate(last_day)))

        for label, orders in (("first day", first_day), ("last day", last_day)):
            got = customer_age_month(orders, acq)
            wrong = got != expected
            if wrong.any():
                i = int(wrong.idxmax())
                self.fail(
                    f"{label} of month {expected[i]} for acquisition "
                    f"{acq[i].date()}: order {orders[i].date()} "
                    f"gave month {got[i]} ({int(wrong.sum())} cases wrong)"
                )

    def test_vectorized_over_many_rows(self):
        orders = pd.Series(pd.to_datetime(["2023-01-09", "2023-01-10", "2023-06-10"]))
        acquired = pd.Series(pd.to_datetime(["2022-12-10"] * 3))
        result = customer_age_month(orders, acquired)
        self.assertEqual(list(result), [1, 2, 7])
        self.assertEqual(result.dtype, "int64")


class TestTimeShift(unittest.TestCase):
    def test_shift_is_a_whole_number_of_weeks(self):
        # Preserves day-of-week, which matters for a business with a weekly rhythm.
        self.assertEqual(TIME_SHIFT_DAYS % 7, 0)

    def test_final_order_lands_in_june_2026(self):
        raw_max = pd.Series([pd.Timestamp("2022-08-30 19:59:00")])
        shifted = apply_time_shift(raw_max).iloc[0]
        self.assertEqual(shifted, pd.Timestamp("2026-06-30 19:59:00"))

    def test_first_order_lands_july_2020(self):
        raw_min = pd.Series([pd.Timestamp("2016-09-01 07:00:00")])
        shifted = apply_time_shift(raw_min).iloc[0]
        self.assertEqual(shifted, pd.Timestamp("2020-07-02 07:00:00"))

    def test_round_trip(self):
        original = pd.Series(pd.to_datetime(["2016-09-01 07:00", "2022-08-30 19:59"]))
        restored = remove_time_shift(apply_time_shift(original))
        pd.testing.assert_series_equal(original, restored)

    def test_preserves_day_of_week(self):
        original = pd.Series(pd.date_range("2016-09-01", periods=400, freq="D"))
        shifted = apply_time_shift(original)
        pd.testing.assert_series_equal(
            original.dt.dayofweek, shifted.dt.dayofweek, check_names=False
        )

    def test_preserves_intervals(self):
        original = pd.Series(pd.to_datetime(["2017-03-04 10:00", "2017-03-09 18:30"]))
        shifted = apply_time_shift(original)
        self.assertEqual(original.diff().iloc[1], shifted.diff().iloc[1])


if __name__ == "__main__":
    unittest.main()
