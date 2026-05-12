# tests/test_logger_state.py
import unittest
import sqlite3
from unittest.mock import patch, MagicMock

from dailydriver.core.logger import (
    get_last_action_time,
    save_pending_start,
    discard_pending_start,
    get_pending_start,
    clear_pending_start,
    start_great_event,
    get_active_great_event,
    clear_great_event,
)

class TestLoggerState(unittest.TestCase):
    def setUp(self):
        # Create a fresh in‑memory database with the meta table
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
        self.conn.commit()
        # Prepare a context manager mock that yields our connection
        self.mock_cm = MagicMock()
        self.mock_cm.__enter__.return_value = self.conn
        self.mock_cm.__exit__.return_value = False

    def tearDown(self):
        self.conn.close()

    # ---------- last_action ----------
    def test_get_last_action_time_none(self):
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            self.assertIsNone(get_last_action_time())

    def test_get_last_action_time_value(self):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('last_action', '123456')")
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            self.assertEqual(get_last_action_time(), 123456)

    # ---------- pending_start ----------
    def test_save_pending_start_and_get(self):
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            save_pending_start()
            ts = get_pending_start()
            self.assertIsNotNone(ts)
            self.assertGreater(ts, 0)

    def test_discard_pending_start_removes(self):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('pending_start', '999')")
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            discard_pending_start()
            self.assertIsNone(get_pending_start())

    def test_clear_pending_start(self):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('pending_start', '111')")
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            clear_pending_start()
            self.assertIsNone(get_pending_start())

    # ---------- great_event ----------
    def test_start_great_event_and_get_active(self):
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            start_great_event(['work', 'focus'])
            start_ts, cats = get_active_great_event()
            self.assertIsNotNone(start_ts)
            self.assertEqual(cats, ['work', 'focus'])

    def test_start_duplicate_great_event_raises(self):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_start', '1')")
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_categories', 'test')")
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            with self.assertRaises(RuntimeError):
                start_great_event(['another'])

    def test_clear_great_event(self):
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_start', '2')")
        self.conn.execute("INSERT INTO meta (key, value) VALUES ('great_event_categories', 'x')")
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            clear_great_event()
            self.assertIsNone(get_active_great_event())

    def test_event_lifecycle(self):
        with patch('dailydriver.core.logger.get_connection_cm', return_value=self.mock_cm):
            # start
            start_great_event(['a', 'b'])
            # read
            ts, cats = get_active_great_event()
            self.assertEqual(cats, ['a', 'b'])
            # clear
            clear_great_event()
            self.assertIsNone(get_active_great_event())

if __name__ == '__main__':
    unittest.main()
