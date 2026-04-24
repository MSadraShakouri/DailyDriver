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

def spread_line(items, width=None, prefix=""):
    """
    Return a string of `items` distributed evenly across `width`.
    First item at left, last at right, others centred in between.
    `prefix` is prepended to the line (e.g., a mosque emoji).
    """
    if width is None:
        width = get_width()
    if not items:
        return prefix
    n = len(items)
    if n == 1:
        return prefix + items[0]
    # total length of all items
    total_len = sum(len(s) for s in items)
    # available gap space (excluding the prefix length)
    gap_space = width - len(prefix) - total_len
    if gap_space < 0:
        # fallback: join with single space, truncate later
        return prefix + " ".join(items)[:width]
    if n == 2:
        # left and right
        result = prefix + items[0] + " " * gap_space + items[1]
    else:
        # n >= 3
        result = prefix + items[0]  # leftmost
        gap_for_others = gap_space // (n - 1)
        remainder = gap_space % (n - 1)
        for i in range(1, n):
            spaces = gap_for_others + (1 if i <= remainder else 0)
            result += " " * spaces + items[i]
    # safety truncate
    if len(result) > width:
        result = result[:width-1] + "…"
    return result
