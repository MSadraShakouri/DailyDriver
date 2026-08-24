"""Unified export items for sleep and naps."""

from __future__ import annotations

from dailydriver.core.export_utils import build_export_item, format_time_range


def export_items(conn, start: int, end: int | None = None) -> list[dict]:
    items: list[dict] = []

    sleep_rows = conn.execute(
        """
        SELECT id, sleep_time, duration_minutes
        FROM sleep_logs
        WHERE sleep_time >= ?
          AND (? IS NULL OR sleep_time <= ?)
        ORDER BY sleep_time, id
        """,
        (start, end, end),
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
          AND (? IS NULL OR start_time <= ?)
        ORDER BY start_time, id
        """,
        (start, end, end),
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
