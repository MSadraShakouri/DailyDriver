from datetime import datetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.prayer.export import export_items


def test_export_items_displays_window_bands(db_path):
    now = int(datetime(2026, 9, 23, 12, 0).timestamp())
    with get_connection_cm(auto=False) as conn:
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time, window_band) VALUES (?, ?, ?, ?, ?, ?)",
            ("fajr", "1405-07-01", "on_time", now, now, "fadilat"),
        )
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time, window_band) VALUES (?, ?, ?, ?, ?, ?)",
            ("dhuhr_asr", "1405-07-01", "on_time", now + 3600, now + 3600, "normal"),
        )
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time, window_band) VALUES (?, ?, ?, ?, ?, ?)",
            ("maghrib_isha", "1405-07-01", "on_time", now + 7200, now + 7200, "late"),
        )
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time, window_band) VALUES (?, ?, ?, ?, ?, ?)",
            ("fajr", "1405-06-30", "qada", now + 10000, now + 10000, "qada"),
        )
        conn.commit()

        items = export_items(conn, start=now - 100)
        assert len(items) == 4
        # fadilat
        assert "✅ Fadilat" in items[0]["details"]
        # normal
        assert "🟡 Normal" in items[1]["details"]
        # late
        assert "🔴 Late" in items[2]["details"]
        # qada
        assert "🕯️ Qada for 30 Shahrivar 1405" in items[3]["details"]
