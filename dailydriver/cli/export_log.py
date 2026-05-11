# dailydriver/cli/export_log.py
"""Export command: write sleep, prayers, and entries to a Markdown or plain‑text file."""
import time, os, re
from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui
import jdatetime
from itertools import groupby

def _jdate_str(ts):
    """Return (jalali_date_str, HH:MM) from a Unix timestamp (local time)."""
    jd = jdatetime.datetime.fromtimestamp(ts)
    return jd.strftime('%d %B %Y'), jd.strftime('%H:%M')

def _fmt_dur(minutes):
    if minutes is None:
        return ''
    return f'{minutes // 60}h {minutes % 60}m'

def _parse_duration(arg):
    """Parse a duration string like '7d', '2w', '3m', '1y' into days."""
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

def _to_markdown(days, sleep_rows, nap_rows, prayer_rows, entry_rows):
    """Build Markdown string with entries grouped by day."""
    lines = []
    lines.append(f'# Export (last {days} days)\n')
    # Sleep table
    lines.append('## Sleep\n')
    if sleep_rows:
        lines.append('| Date | Sleep Time | Wake Time | Duration |')
        lines.append('|------|------------|-----------|----------|')
        for r in sleep_rows:
            date = r['date_str_md']
            start = r['start_time']
            end = r['end_time']
            dur = _fmt_dur(r['duration_minutes'])
            lines.append(f'| {date} | {start} | {end} | {dur} |')
    else:
        lines.append('No sleep data.\n')
    # Naps
    lines.append('\n## Naps\n')
    if nap_rows:
        lines.append('| Date | Start | End | Duration | Description |')
        lines.append('|------|-------|-----|----------|-------------|')
        for r in nap_rows:
            date = r['date_str_md']
            start = r['start_time']
            end = r['end_time']
            dur = _fmt_dur(r['duration_minutes'])
            desc = r['description'] or ''
            lines.append(f'| {date} | {start} | {end} | {dur} | {desc} |')
    else:
        lines.append('No naps.\n')
    # Prayers
    lines.append('\n## Prayers\n')
    if prayer_rows:
        lines.append('| Date | Prayer | Status | Time | Notes |')
        lines.append('|------|--------|--------|------|-------|')
        for r in prayer_rows:
            date = r['date_str_md']
            slot = r['slot_name']
            icon = r['icon']
            time_str = r['time_str']
            notes = r['notes']
            lines.append(f'| {date} | {slot} | {icon} {r["status"]} | {time_str} | {notes} |')
    else:
        lines.append('No prayer data.\n')
    # Journal entries grouped by day
    lines.append('\n## Journal Entries\n')
    if entry_rows:
        # Group by date (first part of 'date_str' which is 'DD Mon YYYY')
        # entry_rows are already sorted by created_at, so they will be in chronological order
        for date, group in groupby(entry_rows, key=lambda r: r['date_str']):
            lines.append(f'### {date}\n')
            for r in group:
                cats = r['categories']
                time_range = r['time_range']
                desc = r['description'].replace('\n', '\n> ')
                lines.append(f'- **{cats}** – *{time_range}*  ')
                lines.append(f'  > {desc}')
            lines.append('')  # blank line after each day
    else:
        lines.append('No journal entries.\n')
    return '\n'.join(lines) + '\n'

def _to_text(days, sleep_rows, nap_rows, prayer_rows, entry_rows):
    """Build plain‑text string with entries grouped by day."""
    lines = []
    lines.append(f'══════ Export (last {days} days) ══════\n')
    lines.append('── Sleep ──')
    for r in sleep_rows:
        date = r['date_str_txt']
        start = r['start_time']
        end = r['end_time']
        dur = _fmt_dur(r['duration_minutes'])
        lines.append(f'{date}   {start} → {end}   ({dur})')
    lines.append('')
    lines.append('── Naps ──')
    for r in nap_rows:
        date = r['date_str_txt']
        start = r['start_time']
        end = r['end_time']
        dur = _fmt_dur(r['duration_minutes'])
        desc = f' - {r["description"]}' if r.get('description') else ''
        lines.append(f'{date}   {start} → {end}   ({dur}){desc}')
    lines.append('')
    lines.append('── Prayers ──')
    for r in prayer_rows:
        date = r['date_str_txt']
        slot = r['slot_name']
        icon = r['icon']
        time_str = r['time_str']
        notes = r['notes']
        line = f'{date}   {icon} {slot} at {time_str}'
        if notes:
            line += f' ({notes})'
        lines.append(line)
    lines.append('')
    lines.append('── Journal Entries ──')
    if entry_rows:
        for date, group in groupby(entry_rows, key=lambda r: r['date_str']):
            lines.append(f'── {date} ──')
            for r in group:
                time_range = r['time_range']
                cats = r['categories']
                desc = r['description']
                lines.append(f'  Time: {time_range}\n  Category: {cats}\n  {desc}\n')
    else:
        lines.append('No journal entries.\n')
    return '\n'.join(lines) + '\n'

def export(cmd):
    """Usage: export <duration> [--txt|--md]   e.g. export 7d --md"""
    parts = cmd.strip().split()
    # defaults
    format = 'md'  # Markdown by default
    duration_arg = None

    # Parse arguments
    i = 1
    while i < len(parts):
        arg = parts[i].lower()
        if arg in ('--txt', '--md'):
            format = arg[2:]   # 'txt' or 'md'
        elif not duration_arg:
            duration_arg = arg
        else:
            current_ui.print_line("Unknown argument: " + parts[i])
            return None
        i += 1

    if not duration_arg:
        current_ui.print_line("Usage: export <duration> [--txt|--md]  (e.g., export 7d, export 2w --txt)")
        return None

    days = _parse_duration(duration_arg)
    if days is None:
        current_ui.print_line("Invalid duration. Use 7d, 2w, 3m, 1y, or a number.")
        return None

    cutoff = int(time.time()) - days * 86400

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Common data queries (reused for both formats)
        # Sleep
        sleep_rows = cur.execute('''
            SELECT jalali_date, sleep_time, wake_time, duration_minutes
            FROM sleep_logs WHERE sleep_time >= ?
            ORDER BY sleep_time
        ''', (cutoff,)).fetchall()
        sleep_data = []
        for r in sleep_rows:
            parts_date = r['jalali_date'].split('-') if r['jalali_date'] else None
            if parts_date and len(parts_date) == 3:
                date_md = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %b %Y')
                date_txt = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %B %Y')
            else:
                date_md = date_txt = 'unknown'
            _, start_t = _jdate_str(r['sleep_time'])
            _, wake_t = _jdate_str(r['wake_time'])
            sleep_data.append({
                'date_str_md': date_md,
                'date_str_txt': date_txt,
                'start_time': start_t,
                'end_time': wake_t,
                'duration_minutes': r['duration_minutes'],
            })

        # Naps
        nap_rows = cur.execute('''
            SELECT jalali_date, start_time, duration_minutes, description
            FROM nap_logs WHERE start_time >= ?
            ORDER BY start_time
        ''', (cutoff,)).fetchall()
        nap_data = []
        for r in nap_rows:
            parts_date = r['jalali_date'].split('-') if r['jalali_date'] else None
            if parts_date and len(parts_date) == 3:
                date_md = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %b %Y')
                date_txt = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %B %Y')
            else:
                date_md = date_txt = 'unknown'
            _, start_t = _jdate_str(r['start_time'])
            if r['duration_minutes'] is not None:
                end_ts = r['start_time'] + r['duration_minutes'] * 60
                _, end_t = _jdate_str(end_ts)
            else:
                end_t = '??:??'
            nap_data.append({
                'date_str_md': date_md,
                'date_str_txt': date_txt,
                'start_time': start_t,
                'end_time': end_t,
                'duration_minutes': r['duration_minutes'],
                'description': r['description'] or '',
            })

        # Prayers
        prayer_rows = cur.execute('''
            SELECT jalali_date, prayer_slot, status, prayer_time, jamaat_location, shak_count
            FROM prayer_logs WHERE logged_at >= ?
            ORDER BY logged_at
        ''', (cutoff,)).fetchall()
        slot_names = {'fajr': 'Fajr', 'dhuhr_asr': 'Dhuhr & Asr', 'maghrib_isha': 'Maghrib & Isha'}
        icons = {'on_time': '✅', 'qada': '🕯️', 'missed': '❌'}
        status_text = {'on_time': 'On‑time', 'qada': 'Qada', 'missed': 'Missed'}
        prayer_data = []
        for r in prayer_rows:
            parts_date = r['jalali_date'].split('-')
            if len(parts_date) == 3:
                date_md = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %b %Y')
                date_txt = jdatetime.date(int(parts_date[0]), int(parts_date[1]), int(parts_date[2])).strftime('%d %B %Y')
            else:
                date_md = date_txt = 'unknown'
            slot = slot_names[r['prayer_slot']]
            icon = icons.get(r['status'], '?')
            status = status_text.get(r['status'], r['status'])
            if r['prayer_time']:
                _, time_str = _jdate_str(r['prayer_time'])
            else:
                time_str = '--:--'
            notes_parts = []
            if r['jamaat_location'] is not None:
                loc = r['jamaat_location'] if r['jamaat_location'] else ''
                notes_parts.append('Jamaat' + (f' at {loc}' if loc else ''))
            if r['shak_count']:
                notes_parts.append(f'Shak {r["shak_count"]}')
            prayer_data.append({
                'date_str_md': date_md,
                'date_str_txt': date_txt,
                'slot_name': slot,
                'icon': icon,
                'status': status,
                'time_str': time_str,
                'notes': ', '.join(notes_parts) if notes_parts else '',
            })

        # Journal entries
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
        entry_data = []
        for r in entry_rows:
            c_date, c_time = _jdate_str(r['created_at'])
            if r['started_at']:
                _, s_time = _jdate_str(r['started_at'])
                dur_str = _fmt_dur(r['duration_minutes']) if r['duration_minutes'] else ''
                if r['duration_minutes'] is not None:
                    finish = r['started_at'] + r['duration_minutes'] * 60
                    _, f_time = _jdate_str(finish)
                else:
                    f_time = '??:??'
                time_range = f'{s_time} → {f_time}'
                if dur_str:
                    time_range += f' ({dur_str})'
            else:
                time_range = 'Logged: ' + c_time
            cats = r['categories'] or '(none)'
            desc = r['description'] or ''
            entry_data.append({
                'date_str': c_date,
                'time_range': time_range,
                'categories': cats,
                'description': desc,
            })

    # Build content
    if format == 'txt':
        content = _to_text(days, sleep_data, nap_data, prayer_data, entry_data)
        ext = 'txt'
    else:
        content = _to_markdown(days, sleep_data, nap_data, prayer_data, entry_data)
        ext = 'md'

    # Write file
    filename = f'export_{duration_arg.strip().lower()}.{ext}'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return f'Exported to {filename} (format: {ext.upper()})'
