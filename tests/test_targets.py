"""Behavioral tests for targets feature (Step 1)."""

import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features.targets import _logic
from dailydriver.features.targets._migrations import migrations


class TestTargetsCore(unittest.TestCase):
    def setUp(self):
        """Set up an in-memory database with migrations applied."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Run migrations
        for mig in migrations():
            mig(self.conn)

        # Patch get_connection_cm in BOTH modules that import it
        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")

        self.mock_logic = self.patcher_logic.start()
        self.mock_utils = self.patcher_utils.start()

        # Both mocks return our in-memory connection
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__enter__.return_value = self.conn

        # Patch the database module too (for safety)
        self.patcher_db = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.mock_db = self.patcher_db.start()
        self.mock_db.return_value.__enter__.return_value = self.conn

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.patcher_db.stop()
        self.conn.close()

    # ========== Test 1: Add Entry ==========
    def test_add_entry(self):
        """Add a nazr entry, verify it exists."""
        eid = _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )
        self.assertIsNotNone(eid)

        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["name"], "Salavat")
        self.assertEqual(entry["kind"], "nazr")
        self.assertEqual(entry["target_total"], 1000)
        self.assertEqual(entry["logged_total"], 0)
        self.assertEqual(entry["interval_type"], "daily")
        self.assertEqual(entry["interval_value"], 1)
        self.assertEqual(entry["target_per_interval"], 100)

    # ========== Test 2: Log Progress Caps at Target ==========
    def test_log_progress_caps_at_target(self):
        """Logging progress caps at the target."""
        eid = _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=50,
        )

        # Log 100, should cap at 50
        result = _logic.log_progress("Salavat", 100)
        self.assertIn("50/50", result)

        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 50)

        # Try logging more — should do nothing
        result = _logic.log_progress("Salavat", 10)
        self.assertIn("Already at target", result)
        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 50)

    # ========== Test 3: Indefinite Target (Habit) ==========
    def test_log_progress_indefinite(self):
        """Habit with NULL target shows N/∞."""
        eid = _logic.add_entry(
            kind="habit",
            name="Anki",
            target_total=None,
        )
        result = _logic.log_progress("Anki", 10)
        self.assertIn("10/∞", result)

        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 10)

        # Log again, should accumulate
        result = _logic.log_progress("Anki", 15)
        self.assertIn("25/∞", result)

        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 25)

    # ========== Test 4: Daily Interval Fulfillment ==========
    def test_interval_fulfillment_daily(self):
        """Daily interval with goal. Logs are summed per day."""
        eid = _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

        # Log 30 on day 1
        _logic.log_progress("Salavat", 30)
        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 30)

        # Get last fulfilled date — should be None (30 < 100)
        last_fulfilled = _logic.get_last_fulfilled_date_for_entry(eid)
        self.assertIsNone(last_fulfilled)

        # Log 70 on day 1 (same day) — total 100
        _logic.log_progress("Salavat", 70)
        entry = _logic.get_entry_by_id(eid)
        self.assertEqual(entry["logged_total"], 100)

        # Last fulfilled date should now be today
        today = jdatetime.date.today()
        last_fulfilled = _logic.get_last_fulfilled_date_for_entry(eid)
        self.assertEqual(last_fulfilled, today)

        # Next due date should be tomorrow (daily interval)
        next_due = _logic.compute_next_due(entry, today)
        self.assertEqual(next_due, today + jdatetime.timedelta(days=1))

    # ========== Extra: Log by Name Validation ==========
    def test_log_by_name_validates_kind(self):
        """Logging with expected_kind validates the entry kind."""
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
        )

        # Log as nazr — should work
        result = _logic.log_progress("Salavat", 10, expected_kind="nazr")
        self.assertIn("Salavat", result)
        self.assertNotIn("not a", result)

        # Log as habit — should fail (wrong kind)
        result = _logic.log_progress("Salavat", 10, expected_kind="habit")
        self.assertIn("not a habit", result)

    # ========== Extra: Name Uniqueness ==========
    def test_name_uniqueness(self):
        """Names must be unique."""
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
        )

        with self.assertRaises(sqlite3.IntegrityError):
            _logic.add_entry(
                kind="habit",
                name="Salavat",  # Duplicate name
                target_total=None,
            )

    # ========== Extra: Weekly Interval ==========
    def test_weekly_interval(self):
        """Weekly interval works."""
        # Today is day 0 (Saturday) — wait, we need to be careful with weekday numbers
        # Let's just add an entry and check that compute_next_due works
        eid = _logic.add_entry(
            kind="nazr",
            name="Weekly",
            target_total=100,
            interval_type="weekly",
            interval_value=0,  # Saturday
            target_per_interval=10,
        )

        entry = _logic.get_entry_by_id(eid)
        today = jdatetime.date.today()
        next_due = _logic.compute_next_due(entry, today)

        # Should be the next Saturday (0)
        # We can't hardcode the exact date, but we can check it's a Saturday
        self.assertIsNotNone(next_due)
        self.assertEqual(next_due.weekday(), 0)  # Saturday is 0 in jdatetime

    # ========== Extra: No Interval ==========
    def test_no_interval(self):
        """Entry with no interval has no due date."""
        eid = _logic.add_entry(
            kind="nazr",
            name="NoInterval",
            target_total=100,
            interval_type=None,
            interval_value=None,
            target_per_interval=None,
        )

        entry = _logic.get_entry_by_id(eid)
        today = jdatetime.date.today()
        next_due = _logic.compute_next_due(entry, today)
        self.assertIsNone(next_due)


# ========== Step 2: Quick Logging Commands ==========

class TestTargetsCommands(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_utils = self.patcher_utils.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__enter__.return_value = self.conn

        # Add a test entry
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
        )
        _logic.add_entry(
            kind="habit",
            name="Anki",
            target_total=None,
        )

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.conn.close()

    def test_nazr_log_command(self):
        """Test 5: nazr log <name> <amount> works."""
        from dailydriver.features.targets import _targets_dispatcher

        # Log 50 to Salavat
        result = _targets_dispatcher("nazr log Salavat 50", kind="nazr")
        self.assertIn("Salavat: 50/1000", result)

        entry = _logic.get_entry_by_name("Salavat")
        self.assertEqual(entry["logged_total"], 50)

    def test_habit_log_command(self):
        """Test 6: habit log <name> <amount> works."""
        from dailydriver.features.targets import _targets_dispatcher

        result = _targets_dispatcher("habit log Anki 10", kind="habit")
        self.assertIn("Anki: 10/∞", result)

        entry = _logic.get_entry_by_name("Anki")
        self.assertEqual(entry["logged_total"], 10)

    def test_log_wrong_kind(self):
        """Test 7: Logging with wrong kind fails."""
        from dailydriver.features.targets import _targets_dispatcher

        # Try to log to a nazr using habit command
        result = _targets_dispatcher("habit log Salavat 10", kind="habit")
        self.assertIn("not a habit", result)

        # Try to log to a habit using nazr command
        result = _targets_dispatcher("nazr log Anki 10", kind="nazr")
        self.assertIn("not a nazr", result)

    def test_log_invalid_amount(self):
        """Test 8: Invalid amount shows error."""
        from dailydriver.features.targets import _targets_dispatcher

        result = _targets_dispatcher("nazr log Salavat abc", kind="nazr")
        self.assertIn("number", result)  # More flexible

        result = _targets_dispatcher("nazr log Salavat -10", kind="nazr")
        self.assertIn("positive", result)


# ========== Step 3: Manager UI ==========

class TestTargetsManager(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_utils = self.patcher_utils.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__enter__.return_value = self.conn

        # Add test entries
        _logic.add_entry(kind="nazr", name="Salavat", target_total=1000)
        _logic.add_entry(kind="habit", name="Anki", target_total=None)
        _logic.add_entry(kind="nazr", name="Dua", target_total=500)

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.conn.close()

    def test_get_all_entries_filtering(self):
        """Test filtering by kind."""
        all_entries = _logic.get_all_entries(kind=None)
        self.assertEqual(len(all_entries), 3)

        nazr_entries = _logic.get_all_entries(kind="nazr")
        self.assertEqual(len(nazr_entries), 2)
        self.assertEqual(nazr_entries[0]["kind"], "nazr")

        habit_entries = _logic.get_all_entries(kind="habit")
        self.assertEqual(len(habit_entries), 1)
        self.assertEqual(habit_entries[0]["kind"], "habit")

    def test_manager_shows_entries(self):
        """Test that entries are returned correctly for display."""
        entries = _logic.get_all_entries(kind=None)
        self.assertEqual(len(entries), 3)

        # Check progress display values
        for e in entries:
            target = e["target_total"]
            logged = e["logged_total"]
            if target is not None:
                self.assertIsInstance(target, int)
            self.assertEqual(logged, 0)

    def test_log_from_manager(self):
        """Test logging from the manager works."""
        # Get the Salavat entry (ID should be 1)
        entries = _logic.get_all_entries(kind="nazr")
        salavat = [e for e in entries if e["name"] == "Salavat"][0]

        result = _logic.log_progress(salavat["name"], 50)
        self.assertIn("50/1000", result)

        entry = _logic.get_entry_by_id(salavat["id"])
        self.assertEqual(entry["logged_total"], 50)


# ========== Step 4: Advanced Manager Features ==========

class TestTargetsAdvanced(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_utils = self.patcher_utils.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__enter__.return_value = self.conn

        # Add a test entry
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.conn.close()

    def test_pause_unpause(self):
        """Test 9: Pause and unpause an entry."""
        entry = _logic.get_entry_by_name("Salavat")
        entry_id = entry["id"]
        today = jdatetime.date.today()

        # Pause for 3 days
        result = _logic.toggle_pause(entry_id, 3)
        self.assertIn("Paused", result)
        self.assertIn("3 days", result)

        # Check paused_until is set
        entry = _logic.get_entry_by_id(entry_id)
        paused_until = entry.get("paused_until")
        self.assertIsNotNone(paused_until)
        y, m, d = map(int, paused_until.split("-"))
        pause_date = jdatetime.date(y, m, d)
        expected = today + jdatetime.timedelta(days=3)
        self.assertEqual(pause_date, expected)

        # Unpause
        result = _logic.toggle_pause(entry_id)
        self.assertIn("Unpaused", result)

        # Check paused_until is cleared
        entry = _logic.get_entry_by_id(entry_id)
        self.assertIsNone(entry.get("paused_until"))

    def test_edit_entry(self):
        """Test 10: Edit an entry."""
        entry = _logic.get_entry_by_name("Salavat")
        entry_id = entry["id"]

        # Edit name
        result = _logic.edit_entry(entry_id, name="SalavatNew")
        self.assertIn("Updated", result)

        entry = _logic.get_entry_by_id(entry_id)
        self.assertEqual(entry["name"], "SalavatNew")

        # Edit target
        result = _logic.edit_entry(entry_id, target_total=2000)
        entry = _logic.get_entry_by_id(entry_id)
        self.assertEqual(entry["target_total"], 2000)

        # Edit interval
        result = _logic.edit_entry(entry_id, interval_type="weekly", interval_value=2)
        entry = _logic.get_entry_by_id(entry_id)
        self.assertEqual(entry["interval_type"], "weekly")
        self.assertEqual(entry["interval_value"], 2)

    def test_delete_cascade(self):
        """Test 11: Delete entry cascades to logs."""
        entry = _logic.get_entry_by_name("Salavat")
        entry_id = entry["id"]

        # Log some progress
        _logic.log_progress("Salavat", 50)

        # Verify log exists
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM target_logs WHERE entry_id = ?", (entry_id,))
            count = cur.fetchone()[0]
            self.assertEqual(count, 1)

        # Delete entry
        result = _logic.delete_entry(entry_id)
        self.assertIn("Deleted", result)

        # Verify entry is gone
        entry = _logic.get_entry_by_id(entry_id)
        self.assertIsNone(entry)

        # Verify logs are gone (cascade)
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM target_logs WHERE entry_id = ?", (entry_id,))
            count = cur.fetchone()[0]
            self.assertEqual(count, 0)


# ========== Step 5: Header Integration ==========

class TestTargetsHeader(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.patcher_logic = patch("dailydriver.features.targets._logic.get_connection_cm")
        self.patcher_utils = patch("dailydriver.features.targets._utils.get_connection_cm")
        self.mock_logic = self.patcher_logic.start()
        self.mock_utils = self.patcher_utils.start()
        self.mock_logic.return_value.__enter__.return_value = self.conn
        self.mock_utils.return_value.__enter__.return_value = self.conn

    def tearDown(self):
        self.patcher_logic.stop()
        self.patcher_utils.stop()
        self.conn.close()

    def test_header_shows_due_entry(self):
        """Test 12: Entry due today shows in header."""
        today = jdatetime.date.today()

        # Add an entry with daily interval, due today
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

        # Get header lines
        from dailydriver.features.targets._header import get_targets_header_lines
        lines = get_targets_header_lines(self.conn)

        # Should show Salavat: 0/100 for today
        self.assertEqual(len(lines), 1)
        self.assertIn("Salavat", lines[0])
        self.assertIn("0/100", lines[0])
        self.assertIn("for today", lines[0])

    def test_header_does_not_show_when_goal_met(self):
        """Test 13: Entry disappears from header after meeting today's goal."""
        today = jdatetime.date.today()

        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

        # Log 100 today (meet the goal)
        _logic.log_progress("Salavat", 100)

        from dailydriver.features.targets._header import get_targets_header_lines
        lines = get_targets_header_lines(self.conn)

        # Should not show (goal already met today)
        self.assertEqual(len(lines), 0)

    def test_header_does_not_show_complete_entry(self):
        """Test 14: Complete entry (logged >= target) does not show in header."""
        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=50,
            interval_type="daily",
            interval_value=1,
            target_per_interval=10,
        )

        # Log to complete it
        _logic.log_progress("Salavat", 50)

        from dailydriver.features.targets._header import get_targets_header_lines
        lines = get_targets_header_lines(self.conn)

        self.assertEqual(len(lines), 0)

    def test_header_does_not_show_paused_entry(self):
        """Test 15: Paused entry does not show in header."""
        today = jdatetime.date.today()

        eid = _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

        # Pause for 3 days
        _logic.toggle_pause(eid, 3)

        from dailydriver.features.targets._header import get_targets_header_lines
        lines = get_targets_header_lines(self.conn)

        self.assertEqual(len(lines), 0)

    def test_header_shows_both_kinds(self):
        """Test 16: Header shows both nazr and habit entries."""
        today = jdatetime.date.today()

        _logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=1000,
            interval_type="daily",
            interval_value=1,
            target_per_interval=100,
        )

        _logic.add_entry(
            kind="habit",
            name="Anki",
            target_total=None,
            interval_type="daily",
            interval_value=1,
            target_per_interval=10,
        )

        from dailydriver.features.targets._header import get_targets_header_lines
        lines = get_targets_header_lines(self.conn)

        # Should show both
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("Salavat" in l for l in lines))
        self.assertTrue(any("Anki" in l for l in lines))
        self.assertTrue(any("🎯" in l for l in lines))
        self.assertTrue(any("📊" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
