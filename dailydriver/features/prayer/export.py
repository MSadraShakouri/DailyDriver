"""Unified export items for prayer logs."""

from __future__ import annotations

import jdatetime

from dailydriver.core.export_utils import build_export_item, jalali_date_time

_SLOT_NAMES = {
    "fajr": "Fajr",
    "dhuhr_asr": "Dhuhr & Asr",
    "maghrib_isha": "Maghrib & Isha",
}
_STATUS_ICONS = {"on_time": "✅", "qada": "🕯️", "missed": "❌"}
_STATUS_TEXT = {"on_time": "On-time", "qada": "Qada", "missed": "Missed"}


def _format_jalali_iso_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        year, month, day = map(int, date_str.split("-"))
        return jdatetime.date(year, month, day).strftime("%d %B %Y")
    except (TypeError, ValueError):
        return date_str


def export_items(conn, cutoff: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, prayer_slot, status, jalali_date, prayer_time, logged_at, jamaat_location, shak_count
        FROM prayer_logs
        WHERE COALESCE(prayer_time, logged_at) >= ?
        ORDER BY COALESCE(prayer_time, logged_at), id
        """,
        (cutoff,),
    ).fetchall()

    items = []
    for row in rows:
        timestamp = row["prayer_time"] if row["prayer_time"] is not None else row["logged_at"]
        display_time = jalali_date_time(timestamp)[1]
        details = []

        status = _STATUS_TEXT.get(row["status"], row["status"])
        if row["status"] == "qada":
            target_date = _format_jalali_iso_date(row["jalali_date"])
            if target_date:
                details.append(f"{_STATUS_ICONS.get(row['status'], '•')} {status} for {target_date}")
            else:
                details.append(f"{_STATUS_ICONS.get(row['status'], '•')} {status}")
        else:
            details.append(f"{_STATUS_ICONS.get(row['status'], '•')} {status}")

        if row["jamaat_location"] is not None:
            location = row["jamaat_location"]
            details.append("Jamaat" + (f" at {location}" if location else ""))
        if row["shak_count"]:
            details.append(f"Shak {row['shak_count']}")

        items.append(
            build_export_item(
                timestamp,
                f"🕌 {_SLOT_NAMES.get(row['prayer_slot'], row['prayer_slot'])}",
                display_time,
                details=", ".join(details),
                sort_key=(timestamp, row["id"]),
            )
        )
    return items
