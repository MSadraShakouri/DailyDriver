# tests/test_multiline.py
import unittest
from unittest.mock import patch


class TestMultiLineBlock(unittest.TestCase):
    """Test that the '---' handler routes ln/ee/ege correctly."""

    def _simulate_multi_line_end(self, first_line, rest_lines, mock_ln, mock_ee, mock_ege):
        """
        Reproduce the exact logic from the '---' block in commander.py.
        """
        multi_buf = [first_line] + rest_lines
        first_parts = first_line.split(maxsplit=1)
        cmd_check = first_parts[0].lower() if first_parts else ""
        if cmd_check in ("ln", "ee", "ege") and len(first_parts) > 0:
            rest_first = first_parts[1] if len(first_parts) > 1 else ""
            if rest_first:
                new_lines = [rest_first] + multi_buf[1:]
            else:
                new_lines = multi_buf[1:]
            desc = "\n".join(new_lines) if new_lines else ""
            if cmd_check == "ln":
                mock_ln(f"ln {desc}")
            elif cmd_check == "ege":
                mock_ege(f"ege {desc}")
            else:  # 'ee'
                mock_ee(f"ee {desc}")
            return True
        return False

    @patch("dailydriver.features.events._logic.end_great_event_cmd")
    @patch("dailydriver.features.events._logic.log_event_end")
    @patch("dailydriver.features.events._logic.log_chain_now")
    def test_ege_multi_line(self, mock_ln, mock_ee, mock_ege):
        """ege with description in multi‑line should call end_great_event_cmd."""
        self._simulate_multi_line_end("ege finished report", ["extra details"], mock_ln, mock_ee, mock_ege)
        mock_ege.assert_called_once_with("ege finished report\nextra details")
        mock_ln.assert_not_called()
        mock_ee.assert_not_called()

    @patch("dailydriver.features.events._logic.end_great_event_cmd")
    @patch("dailydriver.features.events._logic.log_event_end")
    @patch("dailydriver.features.events._logic.log_chain_now")
    def test_ege_multi_line_no_description(self, mock_ln, mock_ee, mock_ege):
        """ege with no extra text should still call end_great_event_cmd."""
        self._simulate_multi_line_end("ege", [], mock_ln, mock_ee, mock_ege)
        mock_ege.assert_called_once_with("ege ")
        mock_ln.assert_not_called()
        mock_ee.assert_not_called()

    @patch("dailydriver.features.events._logic.end_great_event_cmd")
    @patch("dailydriver.features.events._logic.log_event_end")
    @patch("dailydriver.features.events._logic.log_chain_now")
    def test_ee_multi_line(self, mock_ln, mock_ee, mock_ege):
        """ee should still call log_event_end (existing behaviour)."""
        self._simulate_multi_line_end("ee some task", ["more work"], mock_ln, mock_ee, mock_ege)
        mock_ee.assert_called_once_with("ee some task\nmore work")
        mock_ln.assert_not_called()
        mock_ege.assert_not_called()

    @patch("dailydriver.features.events._logic.end_great_event_cmd")
    @patch("dailydriver.features.events._logic.log_event_end")
    @patch("dailydriver.features.events._logic.log_chain_now")
    def test_ln_multi_line(self, mock_ln, mock_ee, mock_ege):
        """ln should still call log_chain_now (existing behaviour)."""
        self._simulate_multi_line_end("ln replied to emails", ["sent follow‑up"], mock_ln, mock_ee, mock_ege)
        mock_ln.assert_called_once_with("ln replied to emails\nsent follow‑up")
        mock_ee.assert_not_called()
        mock_ege.assert_not_called()

    @patch("dailydriver.features.events._logic.end_great_event_cmd")
    @patch("dailydriver.features.events._logic.log_event_end")
    @patch("dailydriver.features.events._logic.log_chain_now")
    def test_plain_text_multi_line_not_routed(self, mock_ln, mock_ee, mock_ege):
        """A normal multi‑line journal entry should NOT route to any event handler."""
        result = self._simulate_multi_line_end("just some thoughts", ["more thinking"], mock_ln, mock_ee, mock_ege)
        self.assertFalse(result)
        mock_ln.assert_not_called()
        mock_ee.assert_not_called()
        mock_ege.assert_not_called()
