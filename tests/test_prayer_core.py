#!/usr/bin/env python3
"""Test prayer slot logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from dailydriver.domains.prayer_core import current_slot

class TestCurrentSlot(unittest.TestCase):

    def test_slot_guessing(self):
        # We can't mock datetime.now() easily without mocking the imports,
        # so we'll test the underlying helper _today_times indirectly by
        # calling current_slot and checking it returns one of the valid slots.
        slot = current_slot()
        valid = {'fajr', 'dhuhr_asr', 'maghrib_isha'}
        self.assertIn(slot, valid)

if __name__ == '__main__':
    unittest.main()
