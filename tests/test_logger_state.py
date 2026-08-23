# tests/test_logger_state.py
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from dailydriver.features.events.state import (
    clear_great_event,
    clear_pending_start,
    discard_pending_start,
    get_active_great_event,
    get_last_action_time,
    get_pending_start,
    save_pending_start,
    start_great_event,
)


class TestLoggerState(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()
        self.mock_cm = MagicMock()
        self.mock_cm.__enter__.return_value = self.conn
        self.mock_cm.__exit__.return_value = False

    def tearDown(self):
        self.conn.close()

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_get_last_action_time_none(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        self.assertIsNone(get_last_action_time())

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_get_last_action_time_value(self, mock_cm):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('last_action', '123456')")
        mock_cm.return_value = self.mock_cm
        self.assertEqual(get_last_action_time(), 123456)

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_save_pending_start_and_get(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        save_pending_start()
        ts = get_pending_start()
        self.assertIsNotNone(ts)
        self.assertGreater(ts, 0)

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_discard_pending_start_removes(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('pending_start', '999')")
        discard_pending_start()
        self.assertIsNone(get_pending_start())

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_clear_pending_start(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('pending_start', '111')")
        clear_pending_start()
        self.assertIsNone(get_pending_start())

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_start_great_event_and_get_active(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        start_great_event(["work", "focus"])
        start_ts, cats = get_active_great_event()
        self.assertIsNotNone(start_ts)
        self.assertEqual(cats, ["work", "focus"])

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_start_duplicate_great_event_raises(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_start', '1')")
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_categories', 'test')")
        with self.assertRaises(RuntimeError):
            start_great_event(["another"])

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_clear_great_event(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_start', '2')")
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_categories', 'x')")
        clear_great_event()
        self.assertIsNone(get_active_great_event())

    @patch("dailydriver.features.events.state.get_connection_cm")
    def test_event_lifecycle(self, mock_cm):
        mock_cm.return_value = self.mock_cm
        start_great_event(["a", "b"])
        ts, cats = get_active_great_event()
        self.assertEqual(cats, ["a", "b"])
        clear_great_event()
        self.assertIsNone(get_active_great_event())
