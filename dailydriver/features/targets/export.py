"""Unified export items for target progress logs."""

from __future__ import annotations

from dailydriver.core.export_utils import build_export_item, jalali_date_time

_KIND_LABELS = {"nazr": "Nazr", "habit": "Habit"}


def export_items(conn, start: int, end: int | None = None) -> list[dict]:
    rows = conn.execute(
        """
        SELECT tl.id, tl.logged_at, tl.amount, te.name, te.kind
        FROM target_logs tl
        JOIN target_entries te ON te.id = tl.entry_id
        WHERE tl.logged_at >= ?
          AND (? IS NULL OR tl.logged_at <= ?)
        ORDER BY tl.logged_at, tl.id
        """,
        (start, end, end),
    ).fetchall()

    items = []
    for row in rows:
        timestamp = row["logged_at"]
        kind = _KIND_LABELS.get(row["kind"], row["kind"])
        items.append(
            build_export_item(
                timestamp,
                f"🎯 {kind}: {row['name']}",
                jalali_date_time(timestamp)[1],
                details=f"+{row['amount']}",
                sort_key=(timestamp, row["id"]),
            )
        )
    return items
