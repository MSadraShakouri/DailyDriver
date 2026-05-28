import os
import sqlite3
import time
from contextlib import contextmanager

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)


def get_db_path() -> str:
    """Return the full path to the SQLite database.
    The environment variable DAILYDRIVER_DB can override the default location."""
    override = os.environ.get("DAILYDRIVER_DB")
    if override:
        return override
    return os.path.join(PROJECT_ROOT, "data", "daily.db")


def get_last_hygiene_time(conn, item):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MAX(e.started_at) as last_time
        FROM entries e
        JOIN entry_categories ec ON e.id = ec.entry_id
        JOIN categories c ON ec.category_id = c.id
        WHERE c.path LIKE ?
    """,
        ("%/" + item,),
    )
    row = cur.fetchone()
    return row["last_time"] if (row and row["last_time"]) else None


class _AutoCommitConnection:
    def __init__(self, conn):
        self._conn = conn

    def commit(self):
        # Record the last action timestamp before committing everything
        try:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_action', ?)",
                (str(int(time.time())),),
            )
        except Exception:
            pass
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection(auto=True):
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not auto:
        return conn
    return _AutoCommitConnection(conn)


@contextmanager
def get_connection_cm(auto=True):
    conn = get_connection(auto=auto)
    try:
        yield conn
    finally:
        conn.close()
