# dailydriver/display/hygiene_nudges.py
import time
from dailydriver.core.database import get_last_hygiene_time

def compute_hygiene_nudges(conn):
    """
    Return a list of human‑readable nudge strings based on hygiene_config.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config ORDER BY item")
    hygiene_items = cur.fetchall()
    nudge_lines = []
    now_ts = int(time.time())

    for item_row in hygiene_items:
        item = item_row['item']
        desired = item_row['desired_interval_days']
        early_enabled = item_row['early_warning_enabled']
        due_today_enabled = item_row['show_due_today']

        last_time = get_last_hygiene_time(conn, item)
        days_since = (now_ts - last_time) // 86400 if last_time else None

        if days_since is None:
            continue

        # Early warning thresholds
        if desired >= 15:
            early_threshold = 3
        elif desired >= 7:
            early_threshold = 2
        elif desired >= 2:
            early_threshold = 1
        else:
            early_threshold = 0

        # 1. Overdue (always show)
        if days_since > desired:
            nudge_lines.append(f"⚠️ {item}: overdue! (last {days_since}d ago)")

        # 2. Due today (optional)
        elif days_since == desired and due_today_enabled:
            nudge_lines.append(f"⚠️ {item}: due today")

        # 3. Early warning (optional)
        elif days_since < desired and early_enabled and early_threshold > 0:
            remaining = desired - days_since
            if remaining <= early_threshold:
                nudge_lines.append(f"⚠️ {item}: due in {remaining}d (last {days_since}d ago)")

    return nudge_lines
