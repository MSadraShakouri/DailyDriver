#!/usr/bin/env python3
"""Simple server for the Event Editor – serves editor.html and handles API."""
import json, os, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FILES = {
    "Jalali":    "events_jalali.json",
    "Gregorian": "events_gregorian.json",
    "Hijri":     "events_hijri.json",
}

def load_file(fname):
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_file(fname, events):
    path = os.path.join(DATA_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

class EditorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/events":
            params = parse_qs(parsed.query)
            fname = params.get("file", [None])[0]
            if fname not in FILES.values():
                self.send_error(400, "Invalid file")
                return
            events = load_file(fname)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(events, ensure_ascii=False).encode())
        else:
            # serve editor.html (must be in same directory as this script)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            html_path = os.path.join(script_dir, "editor.html")
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())

    def do_POST(self):
        if self.path == "/save":
            content_len = int(self.headers["Content-Length"])
            body = self.rfile.read(content_len).decode()
            data = json.loads(body)
            fname = data["file"]
            events = data["events"]
            save_file(fname, events)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_error(404)

if __name__ == "__main__":
    port = 8765
    server = HTTPServer(("127.0.0.1", port), EditorHandler)
    print(f"Editor running at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
