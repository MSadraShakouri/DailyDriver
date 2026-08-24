"""Unified export items for qada progress logs."""

from __future__ import annotations

from dailydriver.core.export_utils import build_export_item, jalali_date_time


def export_items(conn, start: int, end: int | None = None) -> list[dict]:
    rows = conn.execute(
        """
        SELECT ql.id, ql.logged_at, ql.amount, qe.name, qe.kind, qe.slot
        FROM qada_logs ql
        JOIN qada_entries qe ON qe.id = ql.entry_id
        WHERE ql.logged_at >= ?
          AND (? IS NULL OR ql.logged_at <= ?)
        ORDER BY ql.logged_at, ql.id
        """,
        (start, end, end),
    ).fetchall()

    items = []
    for row in rows:
        timestamp = row["logged_at"]
        label = row["name"] if row["kind"] != "fasting" else "Fasting"
        details = f"+{row['amount']}"
        items.append(
            build_export_item(
                timestamp,
                f"📿 Qada: {label}",
                jalali_date_time(timestamp)[1],
                details=details,
                sort_key=(timestamp, row["id"]),
            )
        )
    return items
