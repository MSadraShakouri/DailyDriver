from dailydriver.ui.terminal_ui import current_ui
def show_help():
    current_ui.print_line("═" * 50)
    current_ui.print_line("  DailyDriver — Quick Reference")
    current_ui.print_line("═" * 50)
    current_ui.print_line()

    # ── Logging ──
    current_ui.print_line("📝 Logging")
    current_ui.print_line("  p [time/offset]")
    current_ui.print_line("     Log a prayer (Enter confirms)")
    current_ui.print_line("     p          → current slot")
    current_ui.print_line("     p -15      → 15m before fixed time")
    current_ui.print_line("     p 05:30    → explicitly at 05:30")
    current_ui.print_line()
    current_ui.print_line("  s <sleep> <wake>")
    current_ui.print_line("     Log sleep duration")
    current_ui.print_line("     s 23:00 07:15")
    current_ui.print_line("     s 23-7:15  (compact form)")
    current_ui.print_line("     s n 08:00  (n = now)")
    current_ui.print_line()
    current_ui.print_line("  Any other text = free‑form journal")
    current_ui.print_line("     worked on project 9-12")
    current_ui.print_line()
    current_ui.print_line("  nap [duration]")
    current_ui.print_line("     Log a nap")
    current_ui.print_line("     nap 30m   nap 14:00 14:25")
    current_ui.print_line()

    # ── Prayer management ──
    current_ui.print_line("🕌 Prayer Management")
    current_ui.print_line("  rq")
    current_ui.print_line("     Mark missing prayer as qada")
    current_ui.print_line("  mp")
    current_ui.print_line("     Mark missing as missed or qada")
    current_ui.print_line()

    # ── Events ──
    current_ui.print_line("⏱ Events (start / end / cancel)")
    current_ui.print_line("  se")
    current_ui.print_line("     Start a running event timer")
    current_ui.print_line("  ee [text]")
    current_ui.print_line("     End event & log entry")
    current_ui.print_line("     ee finished report")
    current_ui.print_line("  ce")
    current_ui.print_line("     Cancel the running event")
    current_ui.print_line()

    # ── Chaining ──
    current_ui.print_line("🔗 Chaining")
    current_ui.print_line("  ln [text]")
    current_ui.print_line("     Log entry from last action")
    current_ui.print_line("     to now")
    current_ui.print_line("     ln replied to emails")
    current_ui.print_line()

    # ── Viewing ──
    current_ui.print_line("👁 Viewing & Summaries")
    current_ui.print_line("  today")
    current_ui.print_line("     Show everything logged today")
    current_ui.print_line("  view [filter]")
    current_ui.print_line("     Browse entries (n=next p=prev)")
    current_ui.print_line("     view project")
    current_ui.print_line("     Inside view: id=edit entry")
    current_ui.print_line("  stats")
    current_ui.print_line("     Prayer/sleep/hygiene stats")
    current_ui.print_line()

    # ── Tools ──
    current_ui.print_line("⚙ Tools & Configuration")
    current_ui.print_line("  bd [name date]")
    current_ui.print_line("     Add birthday (Jalali)")
    current_ui.print_line("     bd Ali 1386/05/12")
    current_ui.print_line("     bd Zahra 5/12")
    current_ui.print_line("  t [description]")
    current_ui.print_line("     Add intention / to‑do")
    current_ui.print_line("     t finish report")
    current_ui.print_line("  hygiene")
    current_ui.print_line("     Manage hygiene intervals")
    current_ui.print_line()

    # ── Multi‑line ──
    current_ui.print_line("📄 Multi‑line entries")
    current_ui.print_line("  :m")
    current_ui.print_line("     Start collecting lines")
    current_ui.print_line("  ---")
    current_ui.print_line("     (alone) End & log collected lines")
    current_ui.print_line()

    # ── Other ──
    current_ui.print_line("❓ Other")
    current_ui.print_line("  ?          This help")
    current_ui.print_line("  q          Quit")
    current_ui.print_line()
