"""Travel mode state management — stored in meta table."""

from dailydriver.core.database import get_connection_cm


def is_travel_mode() -> bool:
    """Return True if travel mode is enabled."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'travel_mode'")
        row = cur.fetchone()
        return row is not None and row["value"] == "1"


def set_travel_mode(enabled: bool) -> None:
    """Enable or disable travel mode."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if enabled:
            cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('travel_mode', '1')")
        else:
            cur.execute("DELETE FROM meta WHERE key = 'travel_mode'")
        conn.commit()
