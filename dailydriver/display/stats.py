from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.time_utils import days_ago


def show_stats():
    with get_connection_cm() as conn:
        cur = conn.cursor()

        # --- Prayer: last 30 days ---
        current_ui.print_line("─── Prayer (last 30 days) ───")
        slots = ["fajr", "dhuhr_asr", "maghrib_isha"]
        for slot in slots:
            cur.execute(
                """
                SELECT status, COUNT(*) as cnt
                FROM prayer_logs
                WHERE prayer_slot=? AND logged_at >= ?
                GROUP BY status
            """,
                (slot, days_ago(30)),
            )
            rows = cur.fetchall()
            on_time = qada = missed = 0
            for r in rows:
                if r["status"] == "on_time":
                    on_time = r["cnt"]
                elif r["status"] == "qada":
                    qada = r["cnt"]
                elif r["status"] == "missed":
                    missed = r["cnt"]
            total = on_time + qada + missed
            if total > 0:
                pct = on_time * 100 // total
                current_ui.print_line(f"  {slot}: ✅{on_time}  🕯️{qada}  ❌{missed}  ({pct}% on time)")
            else:
                current_ui.print_line(f"  {slot}: no logs")

        # --- Sleep: last 14 days ---
        current_ui.print_line("\n─── Sleep (last 14 days) ───")
        cutoff = days_ago(14)
        cur.execute(
            """
            SELECT duration_minutes FROM sleep_logs
            WHERE sleep_time >= ?
              AND duration_minutes IS NOT NULL
        """,
            (cutoff,),
        )
        durations = [r["duration_minutes"] for r in cur.fetchall()]
        if durations:
            avg = sum(durations) / len(durations)
            current_ui.print_line(f"  Average: {avg/60:.1f}h ({len(durations)} nights)")
            current_ui.print_line(f"  Best: {max(durations)/60:.1f}h  Worst: {min(durations)/60:.1f}h")
        else:
            current_ui.print_line("  No sleep data.")

        # --- Hygiene: last 30 days adherence ---
        current_ui.print_line("\n─── Hygiene (comparison vs desired) ───")
        cur.execute("SELECT item, desired_interval_days FROM hygiene_config")
        items = cur.fetchall()
        if not items:
            current_ui.print_line("  No hygiene items configured.")
        for item_row in items:
            item = item_row["item"]
            desired = item_row["desired_interval_days"]
            cur.execute(
                """
                SELECT COUNT(*) as cnt FROM entries e
                JOIN entry_categories ec ON e.id = ec.entry_id
                JOIN categories c ON ec.category_id = c.id
                WHERE c.path LIKE ? AND e.started_at >= ?
            """,
                ("%/" + item, days_ago(30)),
            )
            log_count = cur.fetchone()["cnt"]
            expected_count = 30 // desired if desired > 0 else 30
            pct = int(log_count / expected_count * 100) if expected_count > 0 else 0
            current_ui.print_line(f"  {item}: {log_count} logs (expected ~{expected_count}, {pct}%)")

        # --- Entries per category (last 30 days) ---
        current_ui.print_line("\n─── Top Categories (last 30 days) ───")
        cur.execute(
            """
            SELECT c.path, COUNT(*) as cnt
            FROM entries e
            JOIN entry_categories ec ON e.id = ec.entry_id
            JOIN categories c ON ec.category_id = c.id
            WHERE e.created_at >= ?
            GROUP BY c.path
            ORDER BY cnt DESC
            LIMIT 5
        """,
            (days_ago(30),),
        )
        cat_rows = cur.fetchall()
        if not cat_rows:
            current_ui.print_line("  No entries.")
        for cr in cat_rows:
            current_ui.print_line(f"  {cr['path']}: {cr['cnt']} entries")
