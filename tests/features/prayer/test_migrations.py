import sqlite3
from datetime import datetime

from dailydriver.features.prayer.migrations import migrations


def _create_legacy_prayer_logs_table(conn):
    conn.execute("""
        CREATE TABLE prayer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prayer_slot TEXT NOT NULL,
            jalali_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('on_time','qada','missed')),
            logged_at INTEGER,
            prayer_time INTEGER,
            jamaat_location TEXT,
            shak_count INTEGER DEFAULT 0,
            UNIQUE(prayer_slot, jalali_date)
        )
    """)
    conn.commit()


def test_migration_adds_window_band_and_backfills():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        _create_legacy_prayer_logs_table(conn)

        # Insert legacy rows: one fadilat, one qada
        # On 2026-09-23, Dhuhr opens at 11:58, fadilat until ~15:25, sunset ~18:02
        dhuhr_dt = datetime(2026, 9, 23, 12, 15)
        dhuhr_ts = int(dhuhr_dt.timestamp())
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?, ?, ?, ?, ?)",
            ("dhuhr_asr", "1405-07-01", "on_time", dhuhr_ts, dhuhr_ts),
        )
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?, ?, ?, ?, ?)",
            ("fajr", "1405-06-30", "qada", dhuhr_ts, dhuhr_ts),
        )
        conn.commit()

        # Run migration
        migration = migrations()[0]
        migration(conn)

        # Check column exists
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(prayer_logs)")}
        assert "window_band" in columns

        # Check backfilled values
        rows = conn.execute("SELECT prayer_slot, status, window_band FROM prayer_logs ORDER BY id").fetchall()
        assert rows[0]["window_band"] == "fadilat"
        assert rows[1]["window_band"] == "qada"

        # Check idempotency: running migration again succeeds without error
        migration(conn)
    finally:
        conn.close()
