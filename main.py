import os
import sys
from database import init_db
from utils import today_jalali, format_jalali

def clear():
    os.system('clear')

def draw_header():
    today = format_jalali(today_jalali())
    print(f"════════ {today} ════════")
    print("🕌 Fajr ⏳   Dhuhr&Asr ⏳   Maghrib&Isha ⏳")
    print("💤 Sleep: —")
    print("────────────────────────────────────")
    print()

def repl():
    init_db()
    while True:
        clear()
        draw_header()
        cmd = input("> ").strip()
        if cmd.lower() == 'q':
            print("Goodbye.")
            break
        elif cmd == '?':
            input("Help: (not implemented yet) Press Enter to return.")
        else:
            # placeholder – just echo
            input(f"You typed: {cmd}\nPress Enter to continue.")

if __name__ == "__main__":
    repl()
