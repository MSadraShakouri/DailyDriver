#!/usr/bin/env python3
"""Test prayer time interpolation."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from dailydriver.features.prayer._prayer_times import get_approximate_times


class TestPrayerTimes(unittest.TestCase):

    def test_boundary_values(self):
        # January 1
        t = get_approximate_times(1, 1)
        self.assertEqual(t, {"fajr": (4, 42), "dhuhr": (12, 12), "maghrib": (18, 36)})
        # January 22
        t = get_approximate_times(1, 22)
        self.assertEqual(t["fajr"], (4, 9))

    def test_interpolation_mid_month(self):
        t = get_approximate_times(1, 12)
        fajr_min = t["fajr"][0] * 60 + t["fajr"][1]
        self.assertGreaterEqual(fajr_min, 265)
        self.assertLessEqual(fajr_min, 275)

    def test_all_months_return_valid_times(self):
        for m in range(1, 13):
            t = get_approximate_times(m, 1)
            self.assertGreaterEqual(t["fajr"][0], 3)
            self.assertLessEqual(t["fajr"][0], 6)
            self.assertGreaterEqual(t["dhuhr"][0], 11)
            self.assertLessEqual(t["dhuhr"][0], 13)
            self.assertGreaterEqual(t["maghrib"][0], 17)
            self.assertLessEqual(t["maghrib"][0], 21)


if __name__ == "__main__":
    unittest.main()
