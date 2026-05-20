# tests/test_terminal_ui.py
import unittest
from unittest.mock import patch

from dailydriver.ui.terminal_ui import TerminalUI


class TestTerminalUIConfirm(unittest.TestCase):
    def setUp(self):
        self.ui = TerminalUI()

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_default_yes_enter(self, mock_print, mock_input):
        """Enter with default_yes=True → True"""
        mock_input.return_value = ""
        self.assertTrue(self.ui.confirm("Proceed?", default_yes=True))

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_default_yes_n(self, mock_print, mock_input):
        """'n' with default_yes=True → False"""
        mock_input.return_value = "n"
        self.assertFalse(self.ui.confirm("Proceed?", default_yes=True))

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_default_no_y(self, mock_print, mock_input):
        """'y' with default_yes=False → True"""
        mock_input.return_value = "y"
        self.assertTrue(self.ui.confirm("Proceed?", default_yes=False))

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_default_no_enter(self, mock_print, mock_input):
        """Enter with default_yes=False → False"""
        mock_input.return_value = ""
        self.assertFalse(self.ui.confirm("Proceed?", default_yes=False))

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_time_enter(self, mock_print, mock_input):
        """Enter on confirm_time → True"""
        mock_input.return_value = ""
        self.assertTrue(self.ui.confirm_time("09:18", "6m"))

    @patch("builtins.input")
    @patch("dailydriver.ui.terminal_ui.current_ui.print_line")
    def test_confirm_time_n(self, mock_print, mock_input):
        """'n' on confirm_time → False"""
        mock_input.return_value = "n"
        self.assertFalse(self.ui.confirm_time("09:18", "6m"))
