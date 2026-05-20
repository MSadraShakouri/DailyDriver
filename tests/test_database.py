#!/usr/bin/env python3
"""Smoke test for database connection."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from dailydriver.core.database import get_connection_cm

class TestDatabase(unittest.TestCase):

    def test_connection_and_tables(self):
        with get_connection_cm() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cur.fetchall()]
            essential = ['prayer_logs', 'sleep_logs', 'entries', 'categories', 'hygiene_config']
            for tbl in essential:
                self.assertIn(tbl, tables, f"Missing table {tbl}")

if __name__ == '__main__':
    unittest.main()
