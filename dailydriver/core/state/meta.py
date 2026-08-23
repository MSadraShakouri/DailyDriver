"""Low-level helpers for values stored in the meta table."""

from __future__ import annotations

from dailydriver.core.database import get_connection_cm


def get_meta_value(key: str, default: str | None = None, conn=None) -> str | None:
    """Return the stored string value for *key*, or *default* when absent."""

    def _read(connection):
        row = connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row and row["value"] is not None else default

    if conn is not None:
        return _read(conn)
    with get_connection_cm(auto=False) as connection:
        return _read(connection)


def set_meta_value(key: str, value: str | None, conn=None) -> None:
    """Persist *value* for *key* inside the meta table."""

    def _write(connection):
        connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        connection.commit()

    if conn is not None:
        _write(conn)
    else:
        with get_connection_cm(auto=False) as connection:
            _write(connection)


def delete_meta_keys(*keys: str, conn=None) -> None:
    """Delete one or more meta-table keys."""
    if not keys:
        return

    placeholders = ", ".join("?" for _ in keys)

    def _delete(connection):
        connection.execute(f"DELETE FROM meta WHERE key IN ({placeholders})", keys)
        connection.commit()

    if conn is not None:
        _delete(conn)
    else:
        with get_connection_cm(auto=False) as connection:
            _delete(connection)
