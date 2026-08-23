"""Qada command-line parser."""

from dailydriver.core.database import get_connection_cm

from .entries import resolve_entry_id
from .logging import log_fasting, log_prayer_qada, pause_fasting_entry


def qada_command(line: str):
    """Main entry point for the qada command."""
    parts = line.strip().split(maxsplit=2)
    if len(parts) == 1:
        # Bare qada → open manager
        from .manager import show_qada_manager

        show_qada_manager()
        return None

    sub = parts[1].lower()
    if sub == "log":
        return _parse_log(parts[2] if len(parts) > 2 else "")
    if sub == "fasting":
        return _parse_fasting(parts[2] if len(parts) > 2 else "")
    return f"Unknown qada sub-command: {sub}"


def _parse_log(args_str):
    """Parse 'qada log <slot|id> [amount]' and execute."""
    tokens = args_str.strip().split()
    if not tokens:
        return "Usage: qada log <slot|id> [amount]"

    arg = tokens[0]
    amount = 1
    if len(tokens) > 1 and tokens[1].isdigit():
        amount = int(tokens[1])

    entry_id = resolve_entry_id(arg)
    if entry_id is None:
        return f"No qada entry found for '{arg}'."

    return log_prayer_qada(entry_id, amount)


def _parse_fasting(args_str):
    """Parse 'qada fasting yes|no' and execute."""
    tokens = args_str.strip().split()
    if not tokens or tokens[0] not in ("yes", "no"):
        return "Usage: qada fasting yes | qada fasting no"

    response = tokens[0]

    # Find the single fasting entry
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM qada_entries WHERE kind='fasting' ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "No fasting entry found. Add one first."

    entry_id = row["id"]

    if response == "yes":
        return log_fasting(entry_id)
    else:  # "no"
        return pause_fasting_entry()
