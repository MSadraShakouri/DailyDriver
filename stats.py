# DailyDriver/stats.py
import time
from database import get_connection
from utils import days_ago, today_start_ts

def show_stats():
    conn = get_connection()
    cur = conn.cursor()
    now = int(time.time())
    today_start = today_start_ts()

    # --- Prayer: last 30 days ---
    print("─── Prayer (last 30 days) ───")
    slots = ['fajr', 'dhuhr_asr', 'maghrib_isha']
    for slot in slots:
        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM prayer_logs
            WHERE prayer_slot=? AND logged_at >= ?
            GROUP BY status
        """, (slot, days_ago(30)))
        rows = cur.fetchall()
        on_time = qada = missed = 0
        for r in rows:
            if r['status'] == 'on_time': on_time = r['cnt']
            elif r['status'] == 'qada': qada = r['cnt']
            elif r['status'] == 'missed': missed = r['cnt']
        total = on_time + qada + missed
        if total > 0:
            pct = on_time * 100 // total
            print(f"  {slot}: ✅{on_time}  🕯️{qada}  ❌{missed}  ({pct}% on time)")
        else:
            print(f"  {slot}: no logs")

    # --- Sleep: last 14 days ---
    print("\n─── Sleep (last 14 days) ───")
    cutoff = days_ago(14)
    cur.execute("""
        SELECT duration_minutes FROM sleep_logs
        WHERE sleep_time >= ?
          AND duration_minutes IS NOT NULL
    """, (cutoff,))
    durations = [r['duration_minutes'] for r in cur.fetchall()]
    if durations:
        avg = sum(durations) / len(durations)
        print(f"  Average: {avg/60:.1f}h ({len(durations)} nights)")
        print(f"  Best: {max(durations)/60:.1f}h  Worst: {min(durations)/60:.1f}h")
    else:
        print("  No sleep data.")

    # --- Hygiene: last 30 days adherence ---
    print("\n─── Hygiene (comparison vs desired) ───")
    cur.execute("SELECT item, desired_interval_days FROM hygiene_config")
    items = cur.fetchall()
    if not items:
        print("  No hygiene items configured.")
    for item_row in items:
        item = item_row['item']
        desired = item_row['desired_interval_days']
        cur.execute("""
            SELECT COUNT(*) as cnt FROM entries e
            JOIN entry_categories ec ON e.id = ec.entry_id
            JOIN categories c ON ec.category_id = c.id
            WHERE c.path LIKE ? AND e.started_at >= ?
        """, ('%/'+item, days_ago(30)))
        log_count = cur.fetchone()['cnt']
        expected_count = 30 // desired if desired > 0 else 30
        pct = int(log_count / expected_count * 100) if expected_count > 0 else 0
        print(f"  {item}: {log_count} logs (expected ~{expected_count}, {pct}%)")

    # --- Flag frequency: last 30 days ---
    print("\n─── Flags (last 30 days) ───")
    cur.execute("""
        SELECT f.token, COUNT(*) as cnt
        FROM entry_flags ef
        JOIN flags f ON ef.flag_id = f.id
        JOIN entries e ON ef.entry_id = e.id
        WHERE e.created_at >= ?
        GROUP BY f.token
        ORDER BY cnt DESC
        LIMIT 5
    """, (days_ago(30),))
    flag_rows = cur.fetchall()
    if not flag_rows:
        print("  No flags logged.")
    for fr in flag_rows:
        print(f"  {fr['token']}: {fr['cnt']} times")

    # --- Entries per category (last 30 days) ---
    print("\n─── Top Categories (last 30 days) ───")
    cur.execute("""
        SELECT c.path, COUNT(*) as cnt
        FROM entries e
        JOIN entry_categories ec ON e.id = ec.entry_id
        JOIN categories c ON ec.category_id = c.id
        WHERE e.created_at >= ?
        GROUP BY c.path
        ORDER BY cnt DESC
        LIMIT 5
    """, (days_ago(30),))
    cat_rows = cur.fetchall()
    if not cat_rows:
        print("  No entries.")
    for cr in cat_rows:
        print(f"  {cr['path']}: {cr['cnt']} entries")

    conn.close()
