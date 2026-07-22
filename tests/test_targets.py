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


if __name__ == "__main__":
    unittest.main()
