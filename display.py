import shutil

def get_width():
    """Return terminal width (columns), default 80."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80

def print_header(date_str, prayer_str, sleep_str, bday_str, hygiene_str):
    """
    Print the daily header, adapting to terminal width.
    All strings are single lines; we truncate or split if needed.
    """
    w = get_width()

    # --- Top border with centered date ---
    # We want: ════ 4 Ordibehesht 1405 ════
    # where the total length equals w.
    text = f" {date_str} "
    left = (w - len(text)) // 2
    right = w - len(text) - left
    print('═' * left + text + '═' * right)

    # Helper to print a line, truncating to w
    def pline(s):
        if len(s) > w:
            s = s[:w-1] + '…'   # indicate truncation
        print(s)

    # Prayer line (may be long)
    pline(prayer_str)

    # Sleep line
    pline(sleep_str)

    # Birthdays (if present)
    if bday_str:
        pline(bday_str)

    # Hygiene nudges (if present)
    if hygiene_str:
        pline(hygiene_str)

    # Bottom separator
    print('─' * w)
