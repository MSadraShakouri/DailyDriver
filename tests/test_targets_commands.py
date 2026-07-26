"""Tests for targets daily_total, counter_total, counter_reset features."""

import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features.targets import _logic
from dailydriver.features.targets._migrations import migrations


def create_test_entry(conn, name="Salavat", kind="nazr", target_total=1000):
    """Helper to create a target entry directly in the test DB."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO target_entries (kind, name, target_total, logged_total, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (kind, name, target_total, 0, int(jdatetime.datetime.now().timestamp())))
    conn.commit()
    return cur.lastrowid


class TestTargetsCounterHelpers(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_logic.return_value.__exit__.return_value = False

        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_utils = self.patcher_utils.start()
        self.mock_utils.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__exit__.return_value = False

        from dailydriver.features.targets import _utils
        self.utils = _utils

        self.eid = create_test_entry(self.conn, "Salavat", "nazr")

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.conn.close()

    def test_get_counter_value_default(self):
        result = self.utils.get_counter_value(self.eid)
        self.assertEqual(result, 0)

    def test_set_counter_value(self):
        self.utils.set_counter_value(self.eid, 42)
        result = self.utils.get_counter_value(self.eid)
        self.assertEqual(result, 42)

    def test_get_counter_value_after_set(self):
        self.utils.set_counter_value(self.eid, 100)
        result = self.utils.get_counter_value(self.eid)
        self.assertEqual(result, 100)


class TestTargetsDailyTotal(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_logic.return_value.__exit__.return_value = False

        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_utils = self.patcher_utils.start()
        self.mock_utils.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__exit__.return_value = False

        self.shift_patcher = patch("dailydriver.features.targets._logic.get_shifted_today")
        self.mock_shifted = self.shift_patcher.start()
        self.mock_shifted.return_value = jdatetime.date(1405, 5, 3)

        self.ui_patcher = patch("dailydriver.features.targets._logic.current_ui")
        self.mock_ui = self.ui_patcher.start()

        self.eid = create_test_entry(self.conn, "Anki", "habit", target_total=None)

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.shift_patcher.stop()
        self.ui_patcher.stop()
        self.conn.close()

    def test_daily_total_normal(self):
        """daily_total should log the difference between total and today's total."""
        _logic.log_progress("Anki", 5)
        result = _logic.handle_daily_total("daily_total Anki 10")
        self.assertIn("Anki: 10/∞", result)

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 10)

    def test_daily_total_zero_diff(self):
        """Should show message and do nothing if diff is zero."""
        _logic.log_progress("Anki", 10)
        result = _logic.handle_daily_total("daily_total Anki 10")
        self.assertEqual(result, "No change. Nothing logged.")

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 10)

    def test_daily_total_negative_diff(self):
        """Should show warning and NOT log if diff is negative."""
        _logic.log_progress("Anki", 20)
        self.mock_ui.print_line = lambda x: None

        result = _logic.handle_daily_total("daily_total Anki 10")
        self.assertEqual(result, "Negative amount not logged. Please adjust manually.")

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 20)

    def test_daily_total_entry_not_found(self):
        """Should return error if entry not found."""
        result = _logic.handle_daily_total("daily_total NotFound 10")
        self.assertIn("Entry not found", result)

    def test_daily_total_kind_mismatch(self):
        """Should return error if kind doesn't match."""
        result = _logic.handle_daily_total("daily_total Anki 10", kind="nazr")
        self.assertIn("not a nazr", result)


class TestTargetsCounterTotal(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_logic.return_value.__exit__.return_value = False

        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_utils = self.patcher_utils.start()
        self.mock_utils.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__exit__.return_value = False

        self.ui_patcher = patch("dailydriver.features.targets._logic.current_ui")
        self.mock_ui = self.ui_patcher.start()

        self.eid = create_test_entry(self.conn, "Salavat", "nazr", target_total=1000)

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.ui_patcher.stop()
        self.conn.close()

    def test_counter_total_normal(self):
        """counter_total should log diff between value and stored counter."""
        result = _logic.handle_counter_total("counter_total Salavat 50")
        self.assertIn("Salavat: 50/1000", result)

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 50)

        _logic.handle_counter_total("counter_total Salavat 100")
        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 100)

    def test_counter_total_zero_diff(self):
        """Should show message and do nothing if diff is zero."""
        _logic.handle_counter_total("counter_total Salavat 50")
        result = _logic.handle_counter_total("counter_total Salavat 50")
        self.assertEqual(result, "No change. Nothing logged.")

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 50)

    def test_counter_total_negative_diff(self):
        """Should show warning and NOT log if diff is negative."""
        _logic.handle_counter_total("counter_total Salavat 100")
        self.mock_ui.print_line = lambda x: None

        result = _logic.handle_counter_total("counter_total Salavat 50")
        self.assertEqual(result, "Negative amount not logged. Please adjust manually.")

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 100)

    def test_counter_reset(self):
        """counter_reset should set counter to 0 without logging."""
        _logic.handle_counter_total("counter_total Salavat 100")
        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 100)

        result = _logic.handle_counter_reset("counter_reset Salavat")
        self.assertEqual(result, "Counter reset to 0 for Salavat")

        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 100)

        _logic.handle_counter_total("counter_total Salavat 50")
        entry = _logic.get_entry_by_id(self.eid)
        self.assertEqual(entry["logged_total"], 150)

    def test_counter_reset_entry_not_found(self):
        """Should return error if entry not found."""
        result = _logic.handle_counter_reset("counter_reset NotFound")
        self.assertIn("Entry not found", result)


if __name__ == "__main__":
    unittest.main()
