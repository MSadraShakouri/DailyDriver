# tests/test_qada_manager.py
import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import _logic, _manager
from dailydriver.features.qada._migrations import migrations


class TestQadaManager(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.today_j = jdatetime.date.today()
        self.today_str = self.today_j.strftime("%Y-%m-%d")

        # Patch get_connection_cm to return our connection
        self.patcher = patch("dailydriver.features.qada._logic.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_get_all_entries_returns_4(self):
        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(len(entries), 4)
        names = [e["name"] for e in entries]
        self.assertEqual(names, ["Fajr", "Dhuhr/Asr", "Maghrib/Isha", "Fasting"])

    def test_new_entries_have_target_minus_1(self):
        entries = _logic.get_all_entries_with_progress()
        for e in entries:
            self.assertEqual(e["target_total"], -1)
            self.assertEqual(e["logged_total"], 0)
            self.assertEqual(e["progress_display"], "Not set")

    def test_edit_creates_entry(self):
        # First, get entry (will create with -1)
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        # Edit target
        _logic.edit_entry(entry_id, target_total=400)
        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(entries[0]["target_total"], 400)
        self.assertEqual(entries[0]["progress_display"], "0/400")
        self.assertEqual(entries[0]["percentage"], "0.000%")

    def test_log_prayer_updates_progress(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        # Set target and log
        _logic.edit_entry(entry_id, target_total=400)
        _logic.log_prayer_qada(entry_id, 40)

        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(entries[0]["logged_total"], 40)
        self.assertEqual(entries[0]["progress_display"], "40/400")
        self.assertEqual(entries[0]["percentage"], "10.000%")

    def test_log_prayer_caps_at_target(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        _logic.edit_entry(entry_id, target_total=10)
        _logic.log_prayer_qada(entry_id, 15)

        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(entries[0]["logged_total"], 10)
        self.assertEqual(entries[0]["progress_display"], "10/10")
        self.assertEqual(entries[0]["percentage"], "100.000%")
        self.assertTrue(entries[0]["is_complete"])

    def test_edit_higher_target_keeps_logged(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        _logic.edit_entry(entry_id, target_total=10)
        _logic.log_prayer_qada(entry_id, 10)

        # Now increase target
        _logic.edit_entry(entry_id, target_total=20)

        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(entries[0]["logged_total"], 10)
        self.assertEqual(entries[0]["progress_display"], "10/20")
        self.assertEqual(entries[0]["percentage"], "50.000%")

    def test_edit_lower_target_caps_logged(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        _logic.edit_entry(entry_id, target_total=20)
        _logic.log_prayer_qada(entry_id, 15)

        # Decrease target
        _logic.edit_entry(entry_id, target_total=10)

        entries = _logic.get_all_entries_with_progress()
        self.assertEqual(entries[0]["logged_total"], 10)
        self.assertEqual(entries[0]["progress_display"], "10/10")
        self.assertEqual(entries[0]["percentage"], "100.000%")

    def test_pause_updates_until(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        _logic.edit_entry(entry_id, target_total=100)
        pause_until = (self.today_j + jdatetime.timedelta(days=5)).strftime("%Y-%m-%d")
        _logic.edit_entry(entry_id, paused_until=pause_until)

        entries = _logic.get_all_entries_with_progress()
        self.assertTrue(entries[0]["is_paused"])

    def test_unpause_removes_until(self):
        entries = _logic.get_all_entries_with_progress()
        entry_id = entries[0]["id"]

        _logic.edit_entry(entry_id, target_total=100)
        pause_until = (self.today_j + jdatetime.timedelta(days=5)).strftime("%Y-%m-%d")
        _logic.edit_entry(entry_id, paused_until=pause_until)

        _logic.edit_entry(entry_id, paused_until=None)

        entries = _logic.get_all_entries_with_progress()
        self.assertFalse(entries[0]["is_paused"])


if __name__ == "__main__":
    unittest.main()
