# tests/test_hijri_offset.py
import unittest
from unittest.mock import MagicMock, mock_open, patch

import dailydriver.utils.calendar_events as ce_module
from dailydriver.utils.calendar_events import get_hijri_offset, set_hijri_offset


class TestHijriOffset(unittest.TestCase):
    def setUp(self):
        # Reset the module cache after each test so tests don't interfere
        ce_module._cached_events = None

    def test_get_offset_reads_file(self):
        with patch(
            "dailydriver.utils.calendar_events.open",
            mock_open(read_data="2\n1405-02-22\n"),
            create=True,
        ):
            self.assertEqual(get_hijri_offset(), 2)

    def test_get_offset_file_missing(self):
        with patch("dailydriver.utils.calendar_events.open", side_effect=FileNotFoundError):
            self.assertEqual(get_hijri_offset(), 0)

    def test_get_offset_corrupted(self):
        with patch(
            "dailydriver.utils.calendar_events.open",
            mock_open(read_data="abc\n1405-02-22\n"),
            create=True,
        ):
            self.assertEqual(get_hijri_offset(), 0)

    def test_set_offset_writes_file(self):
        m = mock_open()
        fake_today = MagicMock()
        fake_today.strftime.return_value = "1405-02-30"
        with (
            patch("dailydriver.utils.calendar_events.open", m, create=True),
            patch("dailydriver.utils.calendar_events.jdatetime.date") as mock_jd,
        ):
            mock_jd.today.return_value = fake_today
            set_hijri_offset(1)

        # set_hijri_offset writes a single string containing offset and date
        m().write.assert_called_once()
        written_text = m().write.call_args[0][0]
        self.assertIn("1\n", written_text)
        self.assertIn("1405-02-30", written_text)

    def test_set_offset_invalidates_cache(self):
        # Put a fake object in the cache
        ce_module._cached_events = ["fake"]
        with (
            patch("dailydriver.utils.calendar_events.open", mock_open(), create=True),
            patch("dailydriver.utils.calendar_events.jdatetime.date") as mock_jd,
        ):
            fake_today = MagicMock()
            fake_today.strftime.return_value = "1405-02-30"
            mock_jd.today.return_value = fake_today
            set_hijri_offset(-1)

        self.assertIsNone(ce_module._cached_events)
        # Clean up: reset to original state
        ce_module._cached_events = None
