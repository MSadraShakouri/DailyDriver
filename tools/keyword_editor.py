# tools/keyword_editor.py
#!/usr/bin/env python3
"""Keyword editor server – serves keyword_editor.html and handles API calls."""
import json
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "daily.db")
STOPWORDS_PATH = os.path.join(PROJECT_ROOT, "data", "stopwords.txt")

def get_keywords():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT k.id, k.word, c.path AS category, k.count
        FROM keywords k
        JOIN categories c ON k.category_id = c.id
        ORDER BY c.path, k.count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def apply_changes(stop_ids, del_ids):
    import sqlite3
    # read existing stopwords
    existing = set()
    if os.path.exists(STOPWORDS_PATH):
        with open(STOPWORDS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                w = line.strip()
                if w:
                    existing.add(w.lower())

    # get words to add to stopwords
    words_to_add = set()
    if stop_ids:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        placeholders = ','.join('?' for _ in stop_ids)
        rows = conn.execute(f"SELECT DISTINCT word FROM keywords WHERE id IN ({placeholders})", stop_ids).fetchall()
        for r in rows:
            w = r['word'].lower()
            if w not in existing:
                words_to_add.add(w)
        conn.close()

    # append new stopwords
    if words_to_add:
        with open(STOPWORDS_PATH, 'a', encoding='utf-8') as f:
            for w in sorted(words_to_add):
                f.write(w + '\n')

    # delete keywords: union of stop_ids and del_ids
    all_ids = set(stop_ids or []) | set(del_ids or [])
    if all_ids:
        conn = sqlite3.connect(DB_PATH)
        placeholders = ','.join('?' for _ in all_ids)
        conn.execute(f"DELETE FROM keywords WHERE id IN ({placeholders})", list(all_ids))
        conn.commit()
        conn.close()

    return len(words_to_add), len(all_ids)

class EditorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/keywords':
            data = get_keywords()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            # serve the HTML file
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            html_path = os.path.join(script_dir, 'keyword_editor.html')
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())

    def do_POST(self):
        if self.path == '/apply':
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length).decode()
            data = json.loads(body)
            stop_ids = data.get('stop_ids', [])
            del_ids = data.get('del_ids', [])
            added, removed = apply_changes(stop_ids, del_ids)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'added_stopwords': added, 'deleted': removed}).encode())
        else:
            self.send_error(404)

if __name__ == '__main__':
    port = 8767
    server = HTTPServer(('127.0.0.1', port), EditorHandler)
    print(f'Keyword editor running at http://127.0.0.1:{port}')
    webbrowser.open(f'http://127.0.0.1:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
