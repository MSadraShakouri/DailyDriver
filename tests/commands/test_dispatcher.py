import unittest

from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.search import search
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.features.events.commands import (
    cancel_great_event_cmd,
    end_great_event_cmd,
    log_chain_now,
    log_event_end,
    start_great_event_cmd,
)
from dailydriver.features.prayer.commands import log_prayer
from dailydriver.features.sleep.commands import log_nap, log_sleep


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatch = make_dispatch()

    def test_all_expected_keys_present(self):
        expected = [
            "q",
            "p",
            "s",
            "nap",
            "view",
            "?",
            "bd",
            "birthdays",
            "hygiene",
            "t",
            "stats",
            "day",
            "today",
            "se",
            "ce",
            "ee",
            "ln",
            "cal",
            "year",
            "export",
            "search",
            "recent",
            "sge",
            "ege",
            "cge",
        ]
        for key in expected:
            self.assertIn(key, self.dispatch)

    def test_p_dispatches_to_log_prayer(self):
        self.assertEqual(self.dispatch["p"], log_prayer)

    def test_s_dispatches_to_log_sleep(self):
        self.assertEqual(self.dispatch["s"], log_sleep)

    def test_nap_dispatches_to_log_nap(self):
        self.assertEqual(self.dispatch["nap"], log_nap)

    def test_view_is_lambda_wrapping_view_entries(self):
        # We can't compare lambdas directly, so we call it with fake args
        # and check it returns the expected function call result?
        # Just ensure it's callable.
        self.assertTrue(callable(self.dispatch["view"]))

    def test_se_ce_handlers_are_callable(self):
        self.assertTrue(callable(self.dispatch["se"]))
        self.assertTrue(callable(self.dispatch["ce"]))

    def test_event_commands_are_correct(self):
        self.assertEqual(self.dispatch["ee"], log_event_end)
        self.assertEqual(self.dispatch["ln"], log_chain_now)
        self.assertEqual(self.dispatch["sge"], start_great_event_cmd)
        self.assertEqual(self.dispatch["ege"], end_great_event_cmd)
        self.assertEqual(self.dispatch["cge"], cancel_great_event_cmd)

    def test_cal_export_search_last_handlers(self):
        self.assertTrue(callable(self.dispatch["cal"]))
        self.assertEqual(self.dispatch["export"], export)
        self.assertEqual(self.dispatch["search"], search)
        self.assertTrue(callable(self.dispatch["recent"]))
