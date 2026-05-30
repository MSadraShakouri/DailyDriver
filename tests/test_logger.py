# tests/test_logger.py
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from dailydriver.core.logger import log_free_text
from dailydriver.utils.time_parser import TimeInterpretation


class TestLogFreeTextTimeConversion(unittest.TestCase):
    def setUp(self):
        # Fixed now
        self.now = datetime(2026, 5, 20, 14, 30, 0)

        # Mock database connection
        self.mock_conn = MagicMock()
        self.mock_cur = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cur

        # Mock context manager for get_connection_cm
        self.mock_cm = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False

        # Mock _save_entry (to capture arguments)
        self.patch_save = patch("dailydriver.core.logger._save_entry", return_value="Logged OK")
        self.mock_save_entry = self.patch_save.start()

        # Mock find_matching_categories to return some categories
        self.patch_categories = patch(
            "dailydriver.core.logger.find_matching_categories",
            return_value=[("programming", 1)],
        )
        self.patch_categories.start()

        # Mock current_ui (confirm, prompt, print_line)
        self.patch_ui = patch("dailydriver.core.logger.current_ui")
        self.mock_ui = self.patch_ui.start()
        self.mock_ui.confirm_time.return_value = True
        # For category selection, simulate pressing Enter (select first)
        self.mock_ui.prompt.return_value = ""

        # Mock get_last_action_time (used for `l` based expressions)
        self.last_ts = int(datetime(2026, 5, 20, 12, 0, 0).timestamp())
        self.patch_last = patch("dailydriver.core.logger.get_last_action_time", return_value=self.last_ts)
        self.patch_last.start()

        # Mock get_connection_cm
        self.patch_db = patch("dailydriver.core.logger.get_connection_cm", return_value=self.mock_cm)
        self.patch_db.start()

    def tearDown(self):
        self.patch_save.stop()
        self.patch_categories.stop()
        self.patch_ui.stop()
        self.patch_last.stop()
        self.patch_db.stop()

    def test_l6m_passes_timestamp(self):
        # Simulate parser returning a range for "l6m"
        start = datetime(2026, 5, 20, 14, 24, 0)  # now - 6 min
        end = self.now
        interpretation = TimeInterpretation(
            start=start,
            end=end,
            duration_minutes=6,
            label="last 6m (14:24 → 14:30)",
            priority=1,
        )
        with patch(
            "dailydriver.core.logger.parse_time_expressions",
            return_value=[interpretation],
        ):
            result = log_free_text("l6m bathroom")
            self.assertIsNotNone(result)

        # Check that _save_entry was called with started_at as int timestamp
        args, kwargs = self.mock_save_entry.call_args
        self.assertIsNotNone(args)
        conn_arg, cmd_arg, started_at_arg, duration_arg, paths_arg = args[:5]
        self.assertIsInstance(started_at_arg, int)
        self.assertEqual(started_at_arg, int(start.timestamp()))

    @patch("dailydriver.core.logger.datetime")
    def test_no_time_detected_enter_uses_now_timestamp(self, mock_datetime):
        mock_datetime.now.return_value = self.now
        # Parser returns empty list (no time found)
        with patch("dailydriver.core.logger.parse_time_expressions", return_value=[]):
            # User presses Enter at time prompt, then Enter at category prompt
            self.mock_ui.prompt.side_effect = ["", ""]
            result = log_free_text("bathroom")
            self.assertIsNotNone(result)

        args, kwargs = self.mock_save_entry.call_args
        started_at_arg = args[2]
        self.assertIsInstance(started_at_arg, int)
        self.assertEqual(started_at_arg, int(self.now.timestamp()))

    def test_explicit_time_interpretation_selected(self):
        # Multiple interpretations, user selects first (Enter)
        interp1 = TimeInterpretation(
            start=datetime(2026, 5, 20, 9, 18, 0),
            end=datetime(2026, 5, 20, 9, 24, 0),
            duration_minutes=6,
            label="09:18 → 09:24",
            priority=1,
        )
        interp2 = TimeInterpretation(
            start=datetime(2026, 5, 20, 21, 18, 0),
            end=datetime(2026, 5, 20, 21, 24, 0),
            duration_minutes=6,
            label="21:18 → 21:24",
            priority=2,
        )
        with patch(
            "dailydriver.core.logger.parse_time_expressions",
            return_value=[interp1, interp2],
        ):
            self.mock_ui.prompt.return_value = ""  # Enter = first
            result = log_free_text("9:18-9:24 coffee")
            self.assertIsNotNone(result)

        args, kwargs = self.mock_save_entry.call_args
        started_at_arg = args[2]
        self.assertIsInstance(started_at_arg, int)
        self.assertEqual(started_at_arg, int(interp1.start.timestamp()))
        self.assertEqual(args[3], 6)  # duration


if __name__ == "__main__":
    unittest.main()
