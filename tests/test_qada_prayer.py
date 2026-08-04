# tests/test_qada_prayer.py
import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import _logic
from dailydriver.features.qada._migrations import migrations


class TestQadaPrayerLogic(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)
        self.today = jdatetime.date.today()

    def tearDown(self):
        self.conn.close()

    def _add(self, name="fajr", kind="prayer", interval_type="daily", interval_value=None, slot=None, target_total=1):
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, interval_value, slot, target_total, logged_total) VALUES (?,?,?,?,?,?,?)",
            (name, kind, interval_type, interval_value, slot, target_total, 0),
        )
        self.conn.commit()
        return self.conn.execute("SELECT id FROM qada_entries WHERE name=?", (name,)).fetchone()["id"]

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_add_entry_returns_id(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = _logic.add_entry("fajr", "prayer", "daily", slot="fajr")
        self.assertIsNotNone(eid)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_log_prayer_qada_writes_correct_amount(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", "daily", slot="fajr")
        _logic.log_prayer_qada(eid, 1)
        row = self.conn.execute("SELECT amount FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()
        self.assertEqual(row["amount"], 1)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_log_prayer_qada_amount_4_writes_single_row(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", "daily", slot="fajr", target_total=4)
        _logic.log_prayer_qada(eid, 4)
        count = self.conn.execute("SELECT COUNT(*) FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()[0]
        self.assertEqual(count, 1)
        amount = self.conn.execute("SELECT amount FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()["amount"]
        self.assertEqual(amount, 4)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_compute_pending_instance_first_time_uses_reference_date(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", interval_type="n_days", interval_value="3", slot="fajr")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertEqual(inst, self.today)  # Now it should be today

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_compute_pending_instance_after_log_uses_intervals(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", interval_type="n_days", interval_value="3", slot="fajr")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 1),
        )
        self.conn.commit()
        inst = _logic.compute_pending_instance(entry, self.today)
        expected = self.today + jdatetime.timedelta(days=3)
        self.assertEqual(inst, expected)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_log_with_amount_does_not_defer_multiple_days(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", interval_type="daily", interval_value="1", slot="fajr")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 4),
        )
        self.conn.commit()
        inst = _logic.compute_pending_instance(entry, self.today)
        # Amount should NOT affect the next instance – it remains +1 day
        expected = self.today + jdatetime.timedelta(days=1)
        self.assertEqual(inst, expected)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_paused_entry_has_no_pending_instance(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", interval_type="daily", slot="fajr")
        # Set paused_until to tomorrow
        self.conn.execute(
            "UPDATE qada_entries SET paused_until=? WHERE id=?",
            ((self.today + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"), eid),
        )
        self.conn.commit()
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertIsNone(inst)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_unpausing_does_not_reset_schedule(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add("fajr", "prayer", interval_type="daily", slot="fajr")
        # Log once (so last log date is today)
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 1),
        )
        # Pause for 1 day
        self.conn.execute(
            "UPDATE qada_entries SET paused_until=? WHERE id=?",
            ((self.today + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"), eid),
        )
        self.conn.commit()
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        # Should be paused
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertIsNone(inst)

        # Unpause (set paused_until to yesterday)
        self.conn.execute(
            "UPDATE qada_entries SET paused_until=? WHERE id=?",
            ((self.today - jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"), eid),
        )
        self.conn.commit()
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        # After unpausing, the next instance should be based on last log (today+1)
        inst = _logic.compute_pending_instance(entry, self.today)
        expected = self.today + jdatetime.timedelta(days=1)
        self.assertEqual(inst, expected)


if __name__ == "__main__":
    unittest.main()
