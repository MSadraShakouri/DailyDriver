"""Prayer feature migrations."""

from datetime import datetime


def _migration_1(conn):
    """Add window_band column to prayer_logs and backfill existing entries."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(prayer_logs)")
    columns = [row[1] for row in cur.fetchall()]
    if "window_band" not in columns:
        cur.execute(
            "ALTER TABLE prayer_logs ADD COLUMN window_band TEXT CHECK(window_band IN ('fadilat', 'normal', 'late', 'qada', NULL))"
        )

    from dailydriver.features.prayer.windows import get_slot_windows

    cur.execute(
        "SELECT id, prayer_slot, status, prayer_time FROM prayer_logs WHERE window_band IS NULL AND prayer_time IS NOT NULL"
    )
    rows = cur.fetchall()
    for row in rows:
        p_id = row["id"]
        slot = row["prayer_slot"]
        status = row["status"]
        p_time = row["prayer_time"]
        p_dt = datetime.fromtimestamp(p_time)
        if status == "qada" or slot not in ("fajr", "dhuhr_asr", "maghrib_isha"):
            band = "qada"
        else:
            try:
                windows = get_slot_windows(p_dt.date())
                window = windows.get(slot)
                if window:
                    if p_dt < window.green_until:
                        band = "fadilat"
                    elif p_dt < window.red_from:
                        band = "normal"
                    elif p_dt < window.deadline:
                        band = "late"
                    else:
                        band = "qada"
                else:
                    band = "fadilat"
            except Exception:
                band = "fadilat"
        cur.execute("UPDATE prayer_logs SET window_band = ? WHERE id = ?", (band, p_id))
    conn.commit()


def migrations():
    return [_migration_1]
