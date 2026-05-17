# dailydriver/display/display_utils.py
import shutil
import unicodedata
import re
from dailydriver.ui.terminal_ui import current_ui

# ANSI escape sequence pattern
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def strip_ansi(s: str) -> str:
    """Remove ANSI escape codes from a string."""
    return ANSI_ESCAPE.sub('', s)

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
    """Total display width of a string (ANSI codes ignored)."""
    s_clean = strip_ansi(s)
    return sum(char_width(ch) for ch in s_clean)

def pline(s: str):
    """Print a line, truncating to terminal width based on display width."""
    tw = get_width()
    if display_width(s) <= tw:
        current_ui.print_line(s)
        return
    s_clean = strip_ansi(s)
    result = []
    current_width = 0
    for ch in s_clean:
        w = char_width(ch)
        if current_width + w > tw:
            break
        result.append(ch)
        current_width += w
    # Preserve any ANSI codes from the original – we just truncate the visible part
    # For simplicity, we'll just print the truncated clean version; ANSI codes at the ends would be messy.
    # But for pline(), we can just output the truncated clean text. ANSI codes typically don't change width.
    current_ui.print_line(''.join(result) + '…')

def pline_center(s: str):
    """Print a string centered on the terminal, ignoring ANSI codes for width."""
    tw = get_width()
    sw = display_width(s)
    left = (tw - sw) // 2
    current_ui.print_line(' ' * left + s)

def pline_wrap(s: str, indent: int = 0, max_lines: int = 0, first_indent: int | None = None):
    """Print a line, wrapping at word boundaries to fit terminal width.
    If max_lines > 0, print at most that many lines; the last printed
    line will end with '…' if truncation occurs.
    first_indent overrides the indent for the first line only."""
    if first_indent is None:
        first_indent = indent

    tw = get_width()
    if display_width(s) <= tw - first_indent:
        current_ui.print_line(' ' * first_indent + s)
        return

    words = s.split()
    lines = []
    line = ' ' * first_indent
    first = True
    for word in words:
        if display_width(line + word) > tw - 1:
            lines.append(line.rstrip())
            line = ' ' * indent
            first = False
        line += word + ' '
    if line.strip():
        lines.append(line.rstrip())

    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1].rstrip()
        if display_width(last) + 3 <= tw:
            last += '…'
        else:
            last = last[:max(0, display_width(last) - 3)] + '…'
        lines[-1] = last

    for line in lines:
        current_ui.print_line(line)

def wrap_line(prefix: str, text: str, indent: str):
    """Print prefix + text, wrapping at word boundaries.
    Continuation lines start with `indent` (same width as prefix)."""
    words = text.split()
    line = prefix
    for w in words:
        if display_width(line + w) >= get_width():
            current_ui.print_line(line.rstrip())
            line = indent
        line += w + ' '
    if line.rstrip():
        current_ui.print_line(line.rstrip())

def spread_line(items, width=None, prefix="", margins: float = 0.0):
    """Distribute items evenly across the terminal using display widths.
    If margins > 0, the spread line is centered with that fraction of the
    terminal width as left/right margin (e.g., 1/6)."""
    if width is None:
        width = get_width()
    if margins > 0:
        effective_width = int(width * (1 - 2 * margins))
        result = _build_spread(items, effective_width, prefix)
        # center the built line in the full width
        pad = (width - display_width(result)) // 2
        return ' ' * pad + result
    return _build_spread(items, width, prefix)

def _build_spread(items, width, prefix=""):
    """Internal helper – builds the spread string without centering."""
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

def print_header(data: dict, add_separator: bool = True):
    """Print the daily header from a dictionary built by header_data.build()."""
    w = get_width()
    date_str = data['date_str']

    # Build the full prayer line using the prefix and parts
    prayer_str = spread_line(data['prayer_parts'], prefix="🕌 ")

    bday_str = data.get('bday_str', '')

    # New centered date block
    pline_center(data['jalali_line'])
    pline_center(data['separator'])
    current_ui.print_line(data['greg_hijri_line'])   # already centered by spread_line
    current_ui.print_line()                           # breather

    pline(prayer_str)

    sleep_str = data.get('sleep_str', '💤 —')
    nap_str = data.get('nap_str', '')
    if nap_str:
        combined = spread_line([sleep_str, nap_str])
        current_ui.print_line(combined)
    else:
        pline(sleep_str)

    weather_str = data.get('weather_str', '')
    if weather_str:
        pline(weather_str)

    # Great event
    if ge_str := data.get('great_event_str', ''):
        pline(ge_str)

    # Running event
    if event_str := data.get('event_str', ''):
        pline(event_str)

    if bday_str:
        pline(bday_str)
    for line in data.get('hygiene_lines', []):
        pline(line)

    # Prayer nudges
    for nudge in data.get('prayer_nudges', []):
        pline(nudge)

    current_ui.print_line()

    calendar_lines = data.get('calendar_lines', [])
    for line in calendar_lines:
        pline_wrap(line)
    reminders_str = data.get('reminders_str', '')
    if reminders_str:
        pline(reminders_str)

    current_ui.print_line()

    # Bottom bar (right‑aligned, total width = w // 3)
    total_bar_width = w // 5 * 2
    if data.get('is_today', True):
        last_time = data.get('last_entry_time', '')
        if last_time:
            suffix = " Last " + last_time
            dash_len = total_bar_width - display_width(suffix)
            if dash_len < 0:
                dash_len = 0
            visible = '─' * dash_len + suffix
            pad = w - display_width(visible)
            current_ui.print_line(' ' * pad + visible)
        else:
            dash_len = total_bar_width
            visible = '─' * dash_len
            pad = w - display_width(visible)
            current_ui.print_line(' ' * pad + visible)
    else:
        dash_len = total_bar_width
        visible = '─' * dash_len
        pad = w - display_width(visible)
        current_ui.print_line(' ' * pad + visible)

    if add_separator:
        current_ui.print_line()   # blank line before prompt (REPL only)
