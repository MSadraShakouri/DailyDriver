# tests/test_prayer_backlog.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

from dailydriver.domains.prayer_backlog import (
    _get_complete_until,
    _get_unlogged_past_slots,
    _update_complete_until,
)
from dailydriver.domains.prayer_core import PRAYER_SLOTS

TODAY_JALALI = "1405-02-30"
NOW_DT = datetime(2026, 5, 20, 20, 0, 0)


class TestPrayerBacklog(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE prayer_logs ("
            " id INTEGER PRIMARY KEY, prayer_slot TEXT, jalali_date TEXT,"
            " status TEXT, logged_at INTEGER, prayer_time INTEGER)"
        )
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    # ---------- helpers ----------
    def _log_slot(self, date_str, slot, prayer_dt=None):
        if prayer_dt is None:
            prayer_dt = NOW_DT
        self.conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time)" " VALUES (?,?,?,?,?)",
            (
                slot,
                date_str,
                "on_time",
                int(prayer_dt.timestamp()),
                int(prayer_dt.timestamp()),
            ),
        )
        self.conn.commit()

    def _set_complete_until(self, date_str):
        self.conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('prayer_complete_until', ?)",
            (date_str,),
        )
        self.conn.commit()

    # ==================== _update_complete_until ====================

    def test_advance_all_slots_logged(self):
        self._set_complete_until("1405-02-29")
        for date in ["1405-02-29", "1405-02-30"]:
            for slot in PRAYER_SLOTS:
                self._log_slot(date, slot)

        _update_complete_until(self.conn)
        self.assertEqual(_get_complete_until(self.conn), "1405-02-30")

    def test_stop_at_incomplete_day(self):
        self._set_complete_until("1405-02-28")
        for date in ["1405-02-28", "1405-02-29"]:
            for slot in PRAYER_SLOTS:
                self._log_slot(date, slot)
        self._log_slot("1405-02-30", "fajr")

        _update_complete_until(self.conn)
        self.assertEqual(_get_complete_until(self.conn), "1405-02-29")

    def test_initialise_from_earliest_log(self):
        self._log_slot("1405-02-25", "fajr")
        _update_complete_until(self.conn)
        self.assertEqual(_get_complete_until(self.conn), "1405-02-24")

    def test_all_logged_up_to_today(self):
        self._set_complete_until("1405-02-28")
        for date in ["1405-02-28", "1405-02-29", "1405-02-30"]:
            for slot in PRAYER_SLOTS:
                self._log_slot(date, slot)

        _update_complete_until(self.conn)
        self.assertEqual(_get_complete_until(self.conn), "1405-02-30")

    # ==================== _get_unlogged_past_slots ====================

    def test_returns_overdue_slots(self):
        self._set_complete_until("1405-02-28")
        missing = _get_unlogged_past_slots(self.conn, now=NOW_DT)

        self.assertEqual(len(missing), 6)
        self.assertEqual(missing[0][0], "1405-02-30")
        self.assertEqual(missing[0][1], "fajr")

    def test_ignores_slots_before_complete_until(self):
        self._set_complete_until("1405-02-30")
        missing = _get_unlogged_past_slots(self.conn, now=NOW_DT)
        self.assertEqual(missing, [])

    @patch("dailydriver.domains.prayer_backlog.today_jalali", return_value="1405-02-30")
    def test_no_logs_at_all(self, mock_today):
        missing = _get_unlogged_past_slots(self.conn, now=NOW_DT)

        self.assertEqual(missing, [])
        self.assertEqual(_get_complete_until(self.conn), "1405-02-30")
