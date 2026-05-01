import shutil
import unicodedata
from dailydriver.ui.terminal_ui import current_ui

def get_width():
    """Return terminal width in columns, default 80."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80

def char_width(c: str) -> int:
    """Return the display width of a single character (handles emojis)."""
    eaw = unicodedata.east_asian_width(c)
    if eaw in ('W', 'F'):
        return 2
    return 1

def display_width(s: str) -> int:
    """Total display width of a string."""
    return sum(char_width(ch) for ch in s)

def pline(s: str):
    """Print a line, truncating to terminal width based on display width."""
    tw = get_width()
    if display_width(s) <= tw:
        current_ui.print_line(s)
        return
    result = []
    current_width = 0
    for ch in s:
        w = char_width(ch)
        if current_width + w  > tw:
            break
        result.append(ch)
        current_width += w
    current_ui.print_line(''.join(result) + '…')

def spread_line(items, width=None, prefix=""):
    """Distribute items evenly across the terminal using display widths."""
    if width is None:
        width = get_width()
    if not items:
        return prefix

    n = len(items)
    item_widths = [display_width(s) for s in items]
    total_item_width = sum(item_widths)
    prefix_w = display_width(prefix)
    gap_space = width - prefix_w - total_item_width

    if gap_space < 0:
        return prefix + " ".join(items)

    if n == 1:
        return prefix + items[0]

    result = prefix + items[0]
    if n == 2:
        result += " " * gap_space + items[1]
    else:
        gap_each = gap_space // (n - 1)
        remainder = gap_space % (n - 1)
        for i in range(1, n):
            spaces = gap_each + (1 if i <= remainder else 0)
            result += " " * spaces + items[i]
    return result

def print_header(data: dict):
    """Print the daily header from a dictionary built by header_data.build()."""
    w = get_width()
    date_str = data['date_str']

    # Build the full prayer line using the prefix and parts
    prayer_str = spread_line(data['prayer_parts'], prefix="🕌 ")

    sleep_str = data['sleep_str']
    bday_str = data.get('bday_str', '')
    hygiene_str = data.get('hygiene_str', '')

    # Top border with centered date
    text = f" {date_str} "
    left = (w - display_width(text)) // 2
    right = w - display_width(text) - left
    current_ui.print_line('═' * left + text + '═' * right)

    pline(prayer_str)
    pline(sleep_str)

    # Great event
    if ge_str := data.get('great_event_str', ''):
        pline(ge_str)

    # Running event
    if event_str := data.get('event_str', ''):
        pline(event_str)

    if bday_str:
        pline(bday_str)
    if hygiene_str:
        pline(hygiene_str)
    calendar_str = data.get('calendar_str', '')
    if calendar_str:
        pline(calendar_str)
    reminders_str = data.get('reminders_str', '')
    if reminders_str:
        pline(reminders_str)

    # Bottom separator with last entry time (right‑aligned)
    last_time = data.get('last_entry_time', '')
    if last_time:
        text = f" Last: {last_time} "
        dash_count = w - display_width(text)
        if dash_count > 0:
            current_ui.print_line('─' * dash_count + text)
        else:
            pline(text)          # terminal too narrow, just print the text
    else:
        current_ui.print_line('─' * w)
