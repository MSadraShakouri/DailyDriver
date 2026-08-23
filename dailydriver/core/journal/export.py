"""Journal export helpers."""

from __future__ import annotations

from dailydriver.core.export_utils import build_export_item, format_time_range, jalali_date_time



def _display_categories(raw_categories: str | None) -> str:
    """Render journal category paths without the redundant leading ``journal/``."""
    if not raw_categories:
        return "(none)"
    display_paths = []
    for path in [part.strip() for part in raw_categories.split(",") if part.strip()]:
        if path.startswith("journal/"):
            stripped = path[len("journal/") :]
            display_paths.append(stripped or "journal")
        else:
            display_paths.append(path)
    return ", ".join(display_paths) if display_paths else "(none)"



def get_export_items(conn, cutoff: int) -> list[dict]:
    """Return journal entries as unified export timeline items."""
    rows = conn.execute(
        """
        SELECT e.id, e.created_at, e.started_at, e.duration_minutes, e.description,
               GROUP_CONCAT(c.path, ', ') AS categories
        FROM entries e
        LEFT JOIN entry_categories ec ON e.id = ec.entry_id
        LEFT JOIN categories c ON ec.category_id = c.id
        WHERE CASE WHEN e.started_at IS NOT NULL THEN e.started_at ELSE e.created_at END >= ?
        GROUP BY e.id
        ORDER BY CASE WHEN e.started_at IS NOT NULL THEN e.started_at ELSE e.created_at END, e.id
        """,
        (cutoff,),
    ).fetchall()

    items = []
    for row in rows:
        timestamp = row["started_at"] if row["started_at"] is not None else row["created_at"]
        display_time = (
            format_time_range(row["started_at"], row["duration_minutes"])
            if row["started_at"] is not None
            else jalali_date_time(row["created_at"])[1]
        )
        items.append(
            build_export_item(
                timestamp,
                _display_categories(row["categories"]),
                display_time,
                details=(row["description"] or "").strip(),
                sort_key=(timestamp, row["id"]),
            )
        )
    return items
