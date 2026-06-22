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

    def _add(self, name="fajr", kind="prayer", interval_type="daily", interval_value=None):
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, interval_value) VALUES (?,?,?,?)",
            (name, kind, interval_type, interval_value),
        )
        self.conn.commit()
        return self.conn.execute("SELECT id FROM qada_entries WHERE name=?", (name,)).fetchone()["id"]

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_add_entry_returns_id(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = _logic.add_entry("fajr", "prayer", "daily")
        self.assertIsNotNone(eid)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_log_prayer_qada_writes_correct_amount(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add()
        _logic.log_prayer_qada(eid, 1)
        row = self.conn.execute("SELECT amount FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()
        self.assertEqual(row["amount"], 1)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_log_prayer_qada_amount_4_writes_single_row(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add()
        _logic.log_prayer_qada(eid, 4)
        count = self.conn.execute("SELECT COUNT(*) FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()[0]
        self.assertEqual(count, 1)
        amount = self.conn.execute("SELECT amount FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()["amount"]
        self.assertEqual(amount, 4)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_compute_pending_instance_first_time_uses_reference_date(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="n_days", interval_value="3")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertEqual(inst, self.today)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_compute_pending_instance_after_log_uses_intervals(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="n_days", interval_value="3")
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
    def test_log_with_amount_n_defers_next_instance_by_n_intervals(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="n_days", interval_value="1")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 4),
        )
        self.conn.commit()
        inst = _logic.compute_pending_instance(entry, self.today)
        expected = self.today + jdatetime.timedelta(days=4)
        self.assertEqual(inst, expected)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_paused_entry_has_no_pending_instance(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="daily")
        self.conn.execute(
            "UPDATE qada_entries SET paused_from=?, paused_until=? WHERE id=?",
            (self.today.strftime("%Y-%m-%d"), self.today.strftime("%Y-%m-%d"), eid),
        )
        self.conn.commit()
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertIsNone(inst)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_unpause_creates_fresh_instance_from_today(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="daily")
        yesterday = self.today - jdatetime.timedelta(days=1)
        self.conn.execute(
            "UPDATE qada_entries SET paused_from=?, paused_until=? WHERE id=?",
            (yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d"), eid),
        )
        self.conn.commit()
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertEqual(inst, self.today)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_qada_log_slot_name_resolves_to_entry(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(name="fajr")
        resolved = _logic.resolve_entry_id("fajr")
        self.assertEqual(resolved, eid)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_qada_log_numeric_resolves_to_id(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(name="fajr")
        resolved = _logic.resolve_entry_id(str(eid))
        self.assertEqual(resolved, eid)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_delete_cascades_to_logs(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add()
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 1),
        )
        self.conn.commit()
        _logic.delete_entry(eid)
        count = self.conn.execute("SELECT COUNT(*) FROM qada_logs WHERE entry_id=?", (eid,)).fetchone()[0]
        self.assertEqual(count, 0)

    @patch("dailydriver.features.qada._logic.get_connection_cm")
    def test_edit_interval_mid_instance_resets_schedule(self, mock_cm):
        mock_cm.return_value.__enter__.return_value = self.conn
        eid = self._add(interval_type="daily")
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (eid, self.today.strftime("%Y-%m-%d"), 1),
        )
        self.conn.commit()
        _logic.edit_entry(eid, interval_type="weekly", interval_value="2")
        entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE id=?", (eid,)).fetchone())
        inst = _logic.compute_pending_instance(entry, self.today)
        self.assertIsNotNone(inst)
        self.assertEqual(inst.weekday(), 2)  # Monday
