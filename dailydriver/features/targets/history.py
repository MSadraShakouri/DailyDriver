"""Shared utilities for targets feature."""

import jdatetime

from dailydriver.core.database import get_connection_cm


def get_daily_total(entry_id: int, date: jdatetime.date, conn=None) -> int:
    """Return the total amount logged for this entry on a specific date."""
    date_str = date.strftime("%Y-%m-%d")

    def _query(c):
        cur = c.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM target_logs WHERE entry_id = ? AND instance_date = ?",
            (entry_id, date_str),
        )
        row = cur.fetchone()
        return row["total"] if row else 0

    if conn:
        return _query(conn)
    with get_connection_cm(auto=False) as c:
        return _query(c)


def get_last_fulfilled_date(entry_id: int, conn=None) -> jdatetime.date | None:
    """Return the most recent date where the daily total met or exceeded target_per_interval.
    If target_per_interval is NULL, the most recent date with any log > 0.
    """

    def _query(c):
        cur = c.cursor()
        cur.execute("SELECT target_per_interval FROM target_entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        if not row:
            return None
        target = row["target_per_interval"]

        cur.execute(
            """
            SELECT instance_date, SUM(amount) as total
            FROM target_logs
            WHERE entry_id = ?
            GROUP BY instance_date
            ORDER BY instance_date DESC
        """,
            (entry_id,),
        )

        for row in cur.fetchall():
            if target is None:
                if row["total"] > 0:
                    y, m, d = map(int, row["instance_date"].split("-"))
                    return jdatetime.date(y, m, d)
            else:
                if row["total"] >= target:
                    y, m, d = map(int, row["instance_date"].split("-"))
                    return jdatetime.date(y, m, d)
        return None

    if conn:
        return _query(conn)
    with get_connection_cm(auto=False) as c:
        return _query(c)


def get_counter_value(entry_id: int, conn=None) -> int:
    """Return the stored counter value for an entry. Default 0 if not set."""

    def _query(c):
        cur = c.cursor()
        cur.execute("SELECT last_counter_value FROM target_entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        return row["last_counter_value"] if row and row["last_counter_value"] is not None else 0

    if conn:
        return _query(conn)
    with get_connection_cm(auto=False) as c:
        return _query(c)


def set_counter_value(entry_id: int, value: int, conn=None) -> None:
    """Set the counter value for an entry."""

    def _update(c):
        cur = c.cursor()
        cur.execute("UPDATE target_entries SET last_counter_value = ? WHERE id = ?", (value, entry_id))
        c.commit()

    if conn:
        _update(conn)
    else:
        with get_connection_cm(auto=False) as c:
            _update(c)
