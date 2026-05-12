import unittest
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.cli.commands.prayer import log_prayer
from dailydriver.cli.commands.sleep import log_sleep, log_nap
from dailydriver.cli.commands.events import (
    log_event_end, log_chain_now,
    start_great_event_cmd, end_great_event_cmd, cancel_great_event_cmd,
)
from dailydriver.cli.commands.journal import log_free_text
from dailydriver.cli.commands.viewing import view_entries, show_day, show_last, show_today
from dailydriver.cli.commands.search import search
from dailydriver.cli.commands.calendar_cmd import show_calendar, show_year
from dailydriver.cli.commands.stats_cmd import show_stats
from dailydriver.cli.commands.birthday_cmd import add_birthday
from dailydriver.cli.commands.hygiene_cmd import manage_hygiene
from dailydriver.cli.commands.intention_cmd import add_intention
from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.help_cmd import show_help

class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatch = make_dispatch()

    def test_all_expected_keys_present(self):
        expected = [
            'q', 'p', 's', 'nap', 'view', '?', 'bd', 'hygiene', 't',
            'stats', 'day', 'today', 'se', 'ce', 'ee', 'ln', 'cal',
            'year', 'export', 'search', 'last', 'sge', 'ege', 'cge',
        ]
        for key in expected:
            self.assertIn(key, self.dispatch)

    def test_p_dispatches_to_log_prayer(self):
        self.assertEqual(self.dispatch['p'], log_prayer)

    def test_s_dispatches_to_log_sleep(self):
        self.assertEqual(self.dispatch['s'], log_sleep)

    def test_nap_dispatches_to_log_nap(self):
        self.assertEqual(self.dispatch['nap'], log_nap)

    def test_view_is_lambda_wrapping_view_entries(self):
        # We can't compare lambdas directly, so we call it with fake args
        # and check it returns the expected function call result?
        # Just ensure it's callable.
        self.assertTrue(callable(self.dispatch['view']))

    def test_se_ce_handlers_are_callable(self):
        self.assertTrue(callable(self.dispatch['se']))
        self.assertTrue(callable(self.dispatch['ce']))

    def test_event_commands_are_correct(self):
        self.assertEqual(self.dispatch['ee'], log_event_end)
        self.assertEqual(self.dispatch['ln'], log_chain_now)
        self.assertEqual(self.dispatch['sge'], start_great_event_cmd)
        self.assertEqual(self.dispatch['ege'], end_great_event_cmd)
        self.assertEqual(self.dispatch['cge'], cancel_great_event_cmd)

    def test_cal_export_search_last_handlers(self):
        self.assertTrue(callable(self.dispatch['cal']))
        self.assertEqual(self.dispatch['export'], export)
        self.assertEqual(self.dispatch['search'], search)
        self.assertTrue(callable(self.dispatch['last']))
