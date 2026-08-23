# tests/commands/test_events.py
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from dailydriver.features.events.commands import (
    cancel_great_event_cmd,
    end_great_event_cmd,
    log_chain_now,
    log_event_end,
    start_great_event_cmd,
)


class TestEventCommands(unittest.TestCase):
    def setUp(self):
        # Create an in-memory database with meta table for state helpers
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()
        # Context manager mock for get_connection_cm
        self.mock_cm = MagicMock()
        self.mock_cm.__enter__.return_value = self.conn
        self.mock_cm.__exit__.return_value = False

    def tearDown(self):
        self.conn.close()

    # ---------- log_event_end ----------
    @patch("dailydriver.features.events.commands.get_pending_start")
    @patch("dailydriver.features.events.commands.log_free_text")
    def test_log_event_end_no_pending(self, mock_log, mock_pending):
        mock_pending.return_value = None
        result = log_event_end("ee test entry")
        self.assertEqual(result, "No running event to end.")

    @patch("dailydriver.features.events.commands.get_pending_start")
    @patch("dailydriver.features.events.commands.log_free_text")
    @patch("dailydriver.features.events.commands.clear_pending_start")
    def test_log_event_end_success(self, mock_clear, mock_log, mock_pending):
        mock_pending.return_value = 12345
        mock_log.return_value = "Logged"
        result = log_event_end("ee test entry")
        mock_log.assert_called_with("test entry", started_at=12345)
        mock_clear.assert_called_once()
        self.assertEqual(result, "Logged")

    # ---------- log_chain_now ----------
    @patch("dailydriver.features.events.commands.get_last_action_time")
    @patch("dailydriver.features.events.commands.log_free_text")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_log_chain_now_no_previous(self, mock_ui, mock_log, mock_last):
        mock_last.return_value = None
        result = log_chain_now("ln test")
        self.assertEqual(result, "No previous action to chain from.")

    @patch("dailydriver.features.events.commands.get_last_action_time")
    @patch("dailydriver.features.events.commands.log_free_text")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_log_chain_now_success(self, mock_ui, mock_log, mock_last):
        mock_last.return_value = 1000
        log_chain_now("ln chained")
        mock_log.assert_called_with("chained", started_at=1000)

    # ---------- start_great_event_cmd ----------
    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.start_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_start_great_event_already_active(self, mock_ui, mock_start, mock_active):
        mock_active.return_value = (123, ["work"])
        start_great_event_cmd("sge extra")
        mock_ui.print_line.assert_called_with("A great event is already active. Cancel it first (cge).")

    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.start_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_start_great_event_line_with_cats(self, mock_ui, mock_start, mock_active):
        mock_active.return_value = None
        mock_start.return_value = 999
        result = start_great_event_cmd("sge work focus")
        self.assertIn("work", result)
        self.assertIn("focus", result)

    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.start_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_start_great_event_interactive(self, mock_ui, mock_start, mock_active):
        mock_active.return_value = None
        mock_ui.prompt.return_value = "project"
        mock_start.return_value = 100
        result = start_great_event_cmd("sge")
        self.assertIn("project", result)

    # ---------- end_great_event_cmd ----------
    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.log_free_text")
    @patch("dailydriver.features.events.commands.clear_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_end_great_event_no_active(self, mock_ui, mock_clear, mock_log, mock_active):
        mock_active.return_value = None
        end_great_event_cmd("ege done")
        mock_ui.print_line.assert_called_with("No great event is active.")

    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.log_free_text")
    @patch("dailydriver.features.events.commands.clear_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_end_great_event_success(self, mock_ui, mock_clear, mock_log, mock_active):
        mock_active.return_value = (500, ["work"])
        mock_log.return_value = "Great event ended."
        end_great_event_cmd("ege finished report")
        mock_log.assert_called_with("finished report", started_at=500)
        mock_clear.assert_called_once()

    # ---------- cancel_great_event_cmd ----------
    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.clear_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_cancel_great_event_no_active(self, mock_ui, mock_clear, mock_active):
        mock_active.return_value = None
        cancel_great_event_cmd()
        mock_ui.print_line.assert_called_with("No great event active.")

    @patch("dailydriver.features.events.commands.get_active_great_event")
    @patch("dailydriver.features.events.commands.clear_great_event")
    @patch("dailydriver.features.events.commands.current_ui")
    def test_cancel_great_event_success(self, mock_ui, mock_clear, mock_active):
        mock_active.return_value = (600, ["test"])
        result = cancel_great_event_cmd()
        mock_clear.assert_called_once()
        self.assertEqual(result, "Great event cancelled.")
