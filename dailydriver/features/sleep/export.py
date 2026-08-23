"""Unified export items for sleep and naps."""

from __future__ import annotations

from dailydriver.core.export_utils import build_export_item, format_time_range


def export_items(conn, cutoff: int) -> list[dict]:
    items: list[dict] = []

    sleep_rows = conn.execute(
        """
        SELECT id, sleep_time, duration_minutes
        FROM sleep_logs
        WHERE sleep_time >= ?
        ORDER BY sleep_time, id
        """,
        (cutoff,),
    ).fetchall()
    for row in sleep_rows:
        items.append(
            build_export_item(
                row["sleep_time"],
                "💤 Sleep",
                format_time_range(row["sleep_time"], row["duration_minutes"]),
                sort_key=(row["sleep_time"], row["id"], "sleep"),
            )
        )

    nap_rows = conn.execute(
        """
        SELECT id, start_time, duration_minutes, description
        FROM nap_logs
        WHERE start_time >= ?
        ORDER BY start_time, id
        """,
        (cutoff,),
    ).fetchall()
    for row in nap_rows:
        items.append(
            build_export_item(
                row["start_time"],
                "😴 Nap",
                format_time_range(row["start_time"], row["duration_minutes"]),
                details=(row["description"] or "").strip(),
                sort_key=(row["start_time"], row["id"], "nap"),
            )
        )

    return items
