# tests/test_sleep_nap_parser.py
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from dailydriver.domains.nap import log_nap
from dailydriver.domains.sleep import log_sleep
from dailydriver.utils.time_parser import TimeInterpretation


class TestSleepNapParser(unittest.TestCase):
    def setUp(self):
        # Fixed reference times
        self.now = datetime(2026, 5, 20, 14, 30, 0)
        self.last_time = datetime(2026, 5, 20, 12, 0, 0)

        # In‑memory database for sleep / nap tables
        self.sleep_conn = MagicMock()
        self.nap_conn = MagicMock()
        self.sleep_cursor = MagicMock()
        self.nap_cursor = MagicMock()
        self.sleep_conn.cursor.return_value = self.sleep_cursor
        self.nap_conn.cursor.return_value = self.nap_cursor

        # Mock get_connection_cm context manager
        self.mock_cm = MagicMock()
        self.mock_cm.__enter__.return_value = (
            self.sleep_conn
        )  # will be overridden per test
        self.mock_cm.__exit__.return_value = False

    # ---------- helpers ----------
    def _make_interpretation(self, start, end=None, label=""):
        duration = None
        if end:
            duration = int((end - start).total_seconds() // 60)
        return TimeInterpretation(
            start=start, end=end, duration_minutes=duration, label=label, priority=1
        )

    # ---------- log_sleep tests ----------
    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_basic_range(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn

        start = datetime(2026, 5, 20, 23, 0, 0)
        end = datetime(2026, 5, 21, 7, 15, 0)
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_sleep("s 23:00 07:15")
        self.assertIsNotNone(result)
        self.assertIn("Sleep logged", result)
        self.sleep_cursor.execute.assert_called()
        # Check that duration_minutes was inserted
        args, kwargs = self.sleep_cursor.execute.call_args
        sql, params = args[0], args[1]
        self.assertIn("INSERT INTO sleep_logs", sql)
        self.assertEqual(params[1], int(start.timestamp()))  # sleep_time
        self.assertEqual(params[2], int(end.timestamp()))  # wake_time
        self.assertEqual(params[3], 8 * 60 + 15)  # 8h15m

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_dash_range(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn

        start = datetime(2026, 5, 20, 23, 0, 0)
        end = datetime(2026, 5, 21, 7, 15, 0)
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_sleep("s 23-7:15")
        self.assertIsNotNone(result)
        mock_parser.assert_called_once()
        # The old syntax should be converted to "23:00-07:15"? Actually we keep "23-7:15" if already a dash.
        # The parser receives "23-7:15" directly.
        self.assertIn("Sleep logged", result)

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    @patch("dailydriver.domains.sleep.get_last_action_time")
    def test_sleep_last_to_time(self, mock_last, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn
        mock_last.return_value = int(self.last_time.timestamp())

        end = datetime(2026, 5, 20, 9, 0, 0)
        mock_parser.return_value = [self._make_interpretation(self.last_time, end)]
        result = log_sleep("s l-9")
        self.assertIsNotNone(result)
        self.assertIn("Sleep logged", result)

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_to_now(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn

        start = datetime(2026, 5, 20, 23, 0, 0)
        end = self.now
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_sleep("s 23-n")
        self.assertIsNotNone(result)
        self.assertIn("Sleep logged", result)

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    @patch("dailydriver.domains.sleep.get_last_action_time")
    def test_sleep_last_to_now(self, mock_last, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn
        mock_last.return_value = int(self.last_time.timestamp())

        mock_parser.return_value = [self._make_interpretation(self.last_time, self.now)]
        result = log_sleep("s ln")
        self.assertIsNotNone(result)
        self.assertIn("Sleep logged", result)

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    @patch("dailydriver.domains.sleep.get_last_action_time")
    def test_sleep_last_offset(self, mock_last, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn
        mock_last.return_value = int(self.last_time.timestamp())

        end = self.now - timedelta(minutes=10)
        mock_parser.return_value = [self._make_interpretation(self.last_time, end)]
        result = log_sleep("s l--10")
        self.assertIsNotNone(result)
        self.assertIn("Sleep logged", result)

    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_no_duration_rejected(self, mock_ui, mock_parser):
        # Single time point, no end
        start = self.last_time
        mock_parser.return_value = [self._make_interpretation(start)]
        result = log_sleep("s l")
        self.assertIsNone(result)
        mock_ui.print_line.assert_called_with(
            "Duration required. Use a range (e.g., 23:00-7:00, l-9, 23-n, l--10)."
        )

    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_empty_parser_result(self, mock_ui, mock_parser):
        mock_parser.return_value = []
        result = log_sleep("s abc")
        self.assertIsNone(result)
        mock_ui.print_line.assert_called_with(
            "Duration required. Use a range (e.g., 23:00-7:00, l-9, 23-n, l--10)."
        )

    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_no_args(self, mock_ui):
        result = log_sleep("s")
        self.assertIsNone(result)
        mock_ui.print_line.assert_called_with(
            "Usage: S <sleep> <wake>   or   S <sleep>-<wake>"
        )

    @patch("dailydriver.domains.sleep.get_connection_cm")
    @patch("dailydriver.domains.sleep.parse_time_expressions")
    @patch("dailydriver.domains.sleep.current_ui")
    def test_sleep_confirmation_cancelled(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = False  # user cancels
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.sleep_conn

        start = datetime(2026, 5, 20, 23, 0, 0)
        end = datetime(2026, 5, 21, 7, 15, 0)
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_sleep("s 23:00 07:15")
        self.assertIsNone(result)
        # DB should NOT be written
        self.sleep_cursor.execute.assert_not_called()

    # ---------- log_nap tests ----------
    @patch("dailydriver.domains.nap.get_connection_cm")
    @patch("dailydriver.domains.nap.parse_time_expressions")
    @patch("dailydriver.domains.nap.current_ui")
    def test_nap_basic_range(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.nap_conn

        start = datetime(2026, 5, 20, 14, 0, 0)
        end = datetime(2026, 5, 20, 14, 25, 0)
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_nap("nap 14:00 14:25")
        self.assertIsNotNone(result)
        self.assertIn("Nap logged", result)
        self.nap_cursor.execute.assert_called()

    @patch("dailydriver.domains.nap.get_connection_cm")
    @patch("dailydriver.domains.nap.parse_time_expressions")
    @patch("dailydriver.domains.nap.current_ui")
    @patch("dailydriver.domains.nap.get_last_action_time")
    def test_nap_last_offset(self, mock_last, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = True
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.nap_conn
        mock_last.return_value = int(self.last_time.timestamp())

        end = self.now - timedelta(minutes=5)
        mock_parser.return_value = [self._make_interpretation(self.last_time, end)]
        result = log_nap("nap l--5")
        self.assertIsNotNone(result)
        self.assertIn("Nap logged", result)

    @patch("dailydriver.domains.nap.parse_time_expressions")
    @patch("dailydriver.domains.nap.current_ui")
    def test_nap_no_duration_rejected(self, mock_ui, mock_parser):
        start = self.last_time
        mock_parser.return_value = [self._make_interpretation(start)]
        result = log_nap("nap l")
        self.assertIsNone(result)
        mock_ui.print_line.assert_called_with(
            "Duration required. Use a range (e.g., 14:00-14:25, l-14:00, l--5)."
        )

    @patch("dailydriver.domains.nap.current_ui")
    def test_nap_no_args(self, mock_ui):
        result = log_nap("nap")
        self.assertIsNone(result)
        mock_ui.print_line.assert_called_with(
            "Usage: nap <start> <end>   or   nap <start>-<end>"
        )

    @patch("dailydriver.domains.nap.get_connection_cm")
    @patch("dailydriver.domains.nap.parse_time_expressions")
    @patch("dailydriver.domains.nap.current_ui")
    def test_nap_confirmation_cancelled(self, mock_ui, mock_parser, mock_db):
        mock_ui.confirm.return_value = False
        mock_db.return_value = self.mock_cm
        self.mock_cm.__enter__.return_value = self.nap_conn

        start = datetime(2026, 5, 20, 14, 0, 0)
        end = datetime(2026, 5, 20, 14, 25, 0)
        mock_parser.return_value = [self._make_interpretation(start, end)]
        result = log_nap("nap 14:00 14:25")
        self.assertIsNone(result)
        self.nap_cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
