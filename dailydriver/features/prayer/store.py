"""Small database helpers for prayer records."""


def get_prayer_log(conn, slot: str, jalali_date: str):
    """Return the log for *slot* on *jalali_date*, if one exists."""
    return conn.execute(
        "SELECT * FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
        (slot, jalali_date),
    ).fetchone()


def has_prayer_log(conn, slot: str, jalali_date: str) -> bool:
    """Return whether *slot* has been logged on *jalali_date*."""
    return get_prayer_log(conn, slot, jalali_date) is not None
