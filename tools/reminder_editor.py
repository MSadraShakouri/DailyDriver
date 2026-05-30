#!/usr/bin/env python3
"""Simple server for the Reminder Editor – serves reminder_editor.html and handles API."""

import json
import os
import sqlite3
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "daily.db")

FILES = {
    "Jalali": "events_jalali.json",
    "Gregorian": "events_gregorian.json",
    "Hijri": "events_hijri.json",
}


def load_events():
    """Load all events from the three calendar JSON files and attach their reminder level."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load reminder levels into a dict: event_id -> level
    cur.execute("SELECT event_id, level FROM event_reminders")
    levels = {row["event_id"]: row["level"] for row in cur.fetchall()}
    conn.close()

    all_events = []
    for cal_name, fname in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            events = json.load(f)
        for ev in events:
            ev["calendar"] = cal_name.lower()  # 'jalali', 'gregorian', 'hijri'
            ev["level"] = levels.get(ev.get("id"), 0)
            all_events.append(ev)
    return all_events


def set_level(event_id, level):
    """Update (or delete) the reminder level for a given event ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if level == 0:
        cur.execute("DELETE FROM event_reminders WHERE event_id=?", (event_id,))
    else:
        cur.execute(
            "INSERT OR REPLACE INTO event_reminders (event_id, level) VALUES (?, ?)",
            (event_id, level),
        )
    conn.commit()
    conn.close()


class ReminderHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/events":
            events = load_events()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(events, ensure_ascii=False).encode())
        else:
            # Serve reminder_editor.html
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            html_path = os.path.join(script_dir, "reminder_editor.html")
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())

    def do_POST(self):
        if self.path == "/set_level":
            content_len = int(self.headers["Content-Length"])
            body = self.rfile.read(content_len).decode()
            data = json.loads(body)
            event_id = data["event_id"]
            level = data["level"]
            set_level(event_id, level)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_error(404)


if __name__ == "__main__":
    port = 8766
    server = HTTPServer(("127.0.0.1", port), ReminderHandler)
    print(f"Reminder editor running at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
