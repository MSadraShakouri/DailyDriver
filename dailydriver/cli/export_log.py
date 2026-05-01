# dailydriver/cli/export_log.py
"""Export command: write sleep, prayers, and entries to a human‑readable file."""
import time, os
from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui
import jdatetime

def _jdate_str(ts):
    """Return (jalali_date_str, HH:MM) from a Unix timestamp (local time)."""
    jd = jdatetime.datetime.fromtimestamp(ts)
    return jd.strftime('%d %B %Y'), jd.strftime('%H:%M')

def _fmt_dur(minutes):
    if minutes is None:
        return ''
    return f'{minutes // 60}h {minutes % 60}m'

def _parse_duration(arg):
    """Parse a duration string like '7d', '2w', '3m', '1y', '15' into days."""
    arg = arg.strip().lower()
    if not arg:
        return None
    if arg[-1] in ('d', 'w', 'm', 'y'):
        num = arg[:-1]
        if not num.isdigit():
            return None
        num = int(num)
        if arg.endswith('d'):
            return num
        elif arg.endswith('w'):
            return num * 7
        elif arg.endswith('m'):
            return num * 30
        elif arg.endswith('y'):
            return num * 365
    elif arg.isdigit():
        return int(arg)
    return None

def export(cmd):
    """Usage: export <duration>   e.g. export 7d"""
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2:
        current_ui.print_line("Usage: export <duration>  (e.g., export 7d, export 2w)")
        return None
    days = _parse_duration(parts[1])
    if days is None:
        current_ui.print_line("Invalid duration. Use 7d, 2w, 3m, 1y, or a number.")
        return None

    cutoff = int(time.time()) - days * 86400

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # ----- Sleep -----
        sleep_rows = cur.execute('''
            SELECT jalali_date, sleep_time, wake_time, duration_minutes
            FROM sleep_logs WHERE sleep_time >= ?
            ORDER BY sleep_time
        ''', (cutoff,)).fetchall()

        sleep_lines = []
        for r in sleep_rows:
            parts_date = r['jalali_date'].split('-') if r['jalali_date'] else None
            if parts_date and len(parts_date) == 3:
                date_str = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %B %Y')
            else:
                date_str = 'unknown'
            _, start_t = _jdate_str(r['sleep_time'])
            _, wake_t = _jdate_str(r['wake_time'])
            duration = _fmt_dur(r['duration_minutes'])
            sleep_lines.append(f'{date_str}   {start_t} → {wake_t}   ({duration})')

        # ----- Prayers -----
        prayer_rows = cur.execute('''
            SELECT jalali_date, prayer_slot, status, prayer_time, jamaat_location, shak_count
            FROM prayer_logs WHERE logged_at >= ?
            ORDER BY logged_at
        ''', (cutoff,)).fetchall()

        slot_names = {'fajr': 'Fajr', 'dhuhr_asr': 'Dhuhr & Asr', 'maghrib_isha': 'Maghrib & Isha'}
        icons = {'on_time': '✅', 'qada': '🕯️', 'missed': '❌'}

        prayer_lines = []
        for r in prayer_rows:
            parts_date = r['jalali_date'].split('-')
            if len(parts_date) == 3:
                date_str = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %B %Y')
            else:
                date_str = 'unknown'
            slot = slot_names[r['prayer_slot']]
            icon = icons.get(r['status'], '?')
            if r['prayer_time']:
                _, time_str = _jdate_str(r['prayer_time'])
            else:
                time_str = '--:--'
            extra = []
            if r['jamaat_location'] is not None:
                loc = r['jamaat_location'] if r['jamaat_location'] else ''
                extra.append('Jamaat' + (f' at {loc}' if loc else ''))
            if r['shak_count']:
                extra.append(f"Shak {r['shak_count']}")
            line = f'{date_str}   {icon} {slot} at {time_str}'
            if extra:
                line += ' (' + ', '.join(extra) + ')'
            prayer_lines.append(line)

        # ----- Entries -----
        entry_rows = cur.execute('''
            SELECT e.created_at, e.started_at, e.duration_minutes, e.description,
                   GROUP_CONCAT(c.path, ', ') as categories
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            WHERE e.created_at >= ?
            GROUP BY e.id
            ORDER BY e.created_at
        ''', (cutoff,)).fetchall()

        entry_lines = []
        for r in entry_rows:
            c_date, c_time = _jdate_str(r['created_at'])
            if r['started_at']:
                s_date, s_time = _jdate_str(r['started_at'])
                if r['duration_minutes'] is not None:
                    finish = r['started_at'] + r['duration_minutes'] * 60
                    _, f_time = _jdate_str(finish)
                else:
                    f_time = '??:??'
                duration = _fmt_dur(r['duration_minutes']) if r['duration_minutes'] else ''
                time_range = f'{s_time} → {f_time}'
                if duration:
                    time_range += f' ({duration})'
            else:
                s_date, s_time = None, None
                time_range = '(no start time)'
            cats = r['categories'] or '(none)'
            desc = r['description'] or ''
            entry_lines.append(f'{c_date}\n  Time: {time_range} | Logged: {c_time}\n  Category: {cats}\n  {desc}\n')

    # ----- Write file -----
    filename = f'export_{parts[1].strip().lower()}.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('══════ Export (last {} days) ══════\n\n'.format(days))
        f.write('── Sleep ──\n')
        f.write('\n'.join(sleep_lines) + '\n\n')
        f.write('── Prayers ──\n')
        f.write('\n'.join(prayer_lines) + '\n\n')
        f.write('── Journal Entries ──\n')
        f.write('\n'.join(entry_lines) + '\n')

    return f'Exported to {filename}'
