# tools/category_editor.py
#!/usr/bin/env python3
"""Category editor server – serves category_editor.html and handles API calls.

Standalone tool (like edit_events.py, keyword_editor.py, reminder_editor.py).
All write operations are transactional: conn.commit() only on success.

Safety notes
------------
* Renaming a category is NOT a pure cosmetic change.  Category *paths* are
  also persisted as strings in ``meta.great_event_categories`` (space
  joined), and the hygiene feature matches history with
  ``categories.path LIKE '%/' + item``.  A rename therefore:
    - rewrites the old path to the new one inside the great-event meta
      value so entries keep being tagged correctly, and
    - returns a ``warnings`` list if a hygiene item matched the old path
      but no longer matches the new one (its history lookup would break).
* Delete is only allowed when no entry references the category.
* Merge never leaves an entry pointing at the deleted source category and
  never inflates keyword counts even if duplicate (word, category_id) rows
  exist (the keywords table has no UNIQUE constraint).
"""

import json
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from itertools import combinations
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8768
SUGGESTION_LIMIT = 10
ENTRY_PREVIEW_LIMIT = 20
GREAT_EVENT_CATEGORIES_KEY = "great_event_categories"


# ---------------------------------------------------------------------------
# database helpers
# ---------------------------------------------------------------------------

def get_db_path() -> str:
    """Resolve the database path (honours DAILYDRIVER_DB, like the app)."""
    override = os.environ.get("DAILYDRIVER_DB")
    if override:
        return override
    return os.path.join(PROJECT_ROOT, "data", "daily.db")


def _connect():
    import sqlite3

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def normalize_path(raw) -> str:
    """Validate and normalise a category path.  Raises ValueError."""
    if raw is None or not isinstance(raw, str):
        raise ValueError("Name cannot be empty.")
    path = raw.strip()
    if not path:
        raise ValueError("Name cannot be empty.")
    if any(ch.isspace() for ch in path):
        raise ValueError("Name cannot contain spaces or line breaks.")
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise ValueError("Path must not start/end with '/' or contain '//'.")
    return path


# ---------------------------------------------------------------------------
# read operations
# ---------------------------------------------------------------------------

def get_categories():
    """All categories with entry counts, alphabetical by path."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.path, COUNT(ec.entry_id) AS entry_count
            FROM categories c
            LEFT JOIN entry_categories ec ON ec.category_id = c.id
            GROUP BY c.id, c.path
            ORDER BY c.path COLLATE NOCASE, c.path
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_entries_for_category(category_id, limit=ENTRY_PREVIEW_LIMIT):
    """Most recent entries for one category, limited for preview purposes."""
    conn = _connect()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM entry_categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()["n"]
        rows = conn.execute(
            """
            SELECT e.id, e.description
            FROM entries e
            JOIN entry_categories ec ON e.id = ec.entry_id
            WHERE ec.category_id = ?
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT ?
            """,
            (category_id, limit),
        ).fetchall()
        return {
            "entries": [
                {"id": r["id"], "description": r["description"] or ""}
                for r in rows
            ],
            "total": total,
            "has_more": total > limit,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Levenshtein similarity suggestions
# ---------------------------------------------------------------------------

def levenshtein(s1: str, s2: str) -> int:
    """Classic two-row dynamic-programming edit distance."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    previous = list(range(len(s2) + 1))
    for i, ch1 in enumerate(s1, start=1):
        current = [i]
        for j, ch2 in enumerate(s2, start=1):
            insert = previous[j] + 1
            delete = current[j - 1] + 1
            substitute = previous[j - 1] + (ch1 != ch2)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    """1 - edit_distance / max(len(a), len(b)); 1.0 when both are empty."""
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return 1 - (levenshtein(a, b) / longest)


def get_suggestions(only_path=None, limit=SUGGESTION_LIMIT):
    """The ``limit`` most similar unordered category pairs, no minimum score.

    "Top N, to any level" — even a low-similarity pair is shown if it ranks
    in the top ``limit``.  Direction is deterministic (alphabetical by path)
    so the UI can label one side "source" (to be removed) and the other
    "target" (to be kept).  Similarity is computed case-sensitively, which
    deliberately flags case-only duplicates ("Health" vs "health") too.

    If ``only_path`` is given, only pairs involving that path (matched
    case-insensitively) are ranked — used for the suggestion list shown
    inside the merge dialog for one selected category.
    """
    conn = _connect()
    try:
        rows = conn.execute("SELECT id, path FROM categories ORDER BY id").fetchall()
    finally:
        conn.close()

    only = only_path.strip().lower() if only_path else None

    suggestions = []
    for a, b in combinations(rows, 2):
        if only is not None:
            if only not in (a["path"].lower(), b["path"].lower()):
                continue
        score = similarity(a["path"], b["path"])
        first, second = sorted((a, b), key=lambda r: (r["path"].lower(), r["path"]))
        suggestions.append(
            {
                "source_id": first["id"],
                "target_id": second["id"],
                "source_path": first["path"],
                "target_path": second["path"],
                "similarity": round(score, 3),
            }
        )
    suggestions.sort(key=lambda s: (-s["similarity"], s["source_path"], s["target_path"]))
    return suggestions[:limit]


# ---------------------------------------------------------------------------
# write operations (each wrapped in a single transaction)
# ---------------------------------------------------------------------------

def _sync_great_event_meta(conn, old_path, new_path):
    """Keep meta.great_event_categories consistent with a rename/delete.

    The value is space-joined (see core/state/events.py), so paths cannot
    contain spaces and word-level replacement is exact.
    """
    row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", (GREAT_EVENT_CATEGORIES_KEY,)
    ).fetchone()
    if not row or not row["value"]:
        return
    parts = row["value"].split()
    if old_path not in parts:
        return
    parts[parts.index(old_path)] = new_path if new_path else None
    new_value = " ".join(p for p in parts if p is not None)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (GREAT_EVENT_CATEGORIES_KEY, new_value),
    )


def _hygiene_warnings(conn, old_path, new_path):
    """Warn if a hygiene item's path suffix no longer matches after rename.

    Hygiene history is looked up with ``c.path LIKE '%/' + item``, i.e. the
    category path must *end* with "/<item>".
    """
    warnings = []
    if not old_path or "/" not in old_path:
        return warnings
    items = conn.execute("SELECT item FROM hygiene_config").fetchall()
    for item in items:
        name = item["item"]
        if old_path.endswith("/" + name) and new_path and not new_path.endswith("/" + name):
            warnings.append(
                f"Hygiene item '{name}' is matched by path suffix; "
                f"'{new_path}' no longer matches, so its history may no longer be found."
            )
    return warnings


def rename_category(category_id, new_path):
    """Rename one category.  No-op success when the path is unchanged.

    Returns a dict with ``message`` and optional ``warnings``.
    Raises ValueError on validation failures.
    """
    path = normalize_path(new_path)
    conn = _connect()
    try:
        with conn:  # commits on success, rolls back on exception
            cat = conn.execute(
                "SELECT id, path FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if not cat:
                raise ValueError("Category not found.")
            old_path = cat["path"]

            # Exact same name: no-op success (spec §10) without uniqueness
            # checks, so case-variant siblings ("Health" next to "health")
            # cannot block a no-op.
            if path == old_path:
                return {"message": "Renamed.", "warnings": []}

            # Case-insensitive uniqueness, excluding the row being renamed.
            dup = conn.execute(
                "SELECT id FROM categories WHERE LOWER(path) = LOWER(?) AND id != ?",
                (path, category_id),
            ).fetchone()
            if dup:
                raise ValueError("Category already exists.")

            # path != old_path here (also covers case-only changes)
            conn.execute(
                "UPDATE categories SET path = ? WHERE id = ?", (path, category_id)
            )
            _sync_great_event_meta(conn, old_path, path)
            warnings = _hygiene_warnings(conn, old_path, path)
        return {"message": "Renamed.", "warnings": warnings}
    finally:
        conn.close()


def merge_categories(source_id, target_id, new_name):
    """Merge source into target, optionally renaming the result.

    Single transaction:
      1. drop source refs from entries that already have target (PK conflict)
      2. point remaining entry refs at target
      3. merge keywords (sum counts on the same word, insert otherwise;
         scoped to one row because keywords has no UNIQUE(word, category_id))
      4. delete source keywords
      5. delete source category
      6. rename target to the chosen name (after the source is gone, so a
         result name equal to the old source path is legal)
    """
    result_path = normalize_path(new_name)
    conn = _connect()
    try:
        with conn:
            src = conn.execute(
                "SELECT id, path FROM categories WHERE id = ?", (source_id,)
            ).fetchone()
            tgt = conn.execute(
                "SELECT id, path FROM categories WHERE id = ?", (target_id,)
            ).fetchone()
            if not src:
                raise ValueError("Source category not found.")
            if not tgt:
                raise ValueError("Target category not found.")
            if src["id"] == tgt["id"]:
                raise ValueError("Source and target are the same category.")

            # Uniqueness: exclude source (about to be deleted) and target
            # (the surviving row, which may simply keep its own name).
            dup = conn.execute(
                "SELECT id FROM categories WHERE LOWER(path) = LOWER(?)"
                " AND id != ? AND id != ?",
                (result_path, source_id, target_id),
            ).fetchone()
            if dup:
                raise ValueError("Category already exists.")

            # 1. remove duplicate category references per entry
            conn.execute(
                """
                DELETE FROM entry_categories
                WHERE category_id = ?
                  AND entry_id IN (
                      SELECT entry_id FROM entry_categories WHERE category_id = ?
                  )
                """,
                (source_id, target_id),
            )
            # 2. update remaining entries
            conn.execute(
                "UPDATE entry_categories SET category_id = ? WHERE category_id = ?",
                (target_id, source_id),
            )
            # 3. merge keywords
            for kw in conn.execute(
                "SELECT word, COALESCE(count, 1) AS count"
                " FROM keywords WHERE category_id = ?",
                (source_id,),
            ).fetchall():
                existing = conn.execute(
                    "SELECT id FROM keywords WHERE word = ? AND category_id = ?"
                    " ORDER BY id LIMIT 1",
                    (kw["word"], target_id),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE keywords SET count = count + ? WHERE id = ?",
                        (kw["count"], existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO keywords (word, category_id, count) VALUES (?, ?, ?)",
                        (kw["word"], target_id, kw["count"]),
                    )
            # 4. delete source keywords
            conn.execute("DELETE FROM keywords WHERE category_id = ?", (source_id,))
            # 5. delete source category (FKs ON: fails loudly if step 2 missed a ref)
            conn.execute("DELETE FROM categories WHERE id = ?", (source_id,))
            # 6. rename target if the chosen name differs (case-insensitive)
            if result_path.lower() != tgt["path"].lower():
                conn.execute(
                    "UPDATE categories SET path = ? WHERE id = ?",
                    (result_path, target_id),
                )
        return {
            "message": (
                f"Merged '{src['path']}' into '{result_path}'."
                if result_path.lower() != tgt["path"].lower()
                else f"Merged '{src['path']}' into '{tgt['path']}'."
            )
        }
    finally:
        conn.close()


def delete_category(category_id):
    """Delete a category only if no entry references it.  Also deletes its
    keywords and removes it from the great-event meta list."""
    conn = _connect()
    try:
        with conn:
            cat = conn.execute(
                "SELECT id, path FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if not cat:
                raise ValueError("Category not found.")
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM entry_categories WHERE category_id = ?",
                (category_id,),
            ).fetchone()["n"]
            if count:
                raise ValueError(
                    f"Category '{cat['path']}' is referenced by {count} "
                    "entr" + ("y" if count == 1 else "ies") + "; delete entries first."
                )
            # keywords first, then the category itself
            conn.execute("DELETE FROM keywords WHERE category_id = ?", (category_id,))
            conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            _sync_great_event_meta(conn, cat["path"], None)
        return {"message": f"Deleted '{cat['path']}'."}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

class EditorHandler(SimpleHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(script_dir, "category_editor.html"), "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object.")
        return data

    def do_GET(self):
        try:
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._send_html()
            elif url.path == "/categories":
                self._send_json(get_categories())
            elif url.path == "/entries":
                params = parse_qs(url.query)
                raw = (params.get("category_id") or [""])[0]
                try:
                    category_id = int(raw)
                except ValueError:
                    raise ValueError("category_id must be an integer.")
                self._send_json(get_entries_for_category(category_id))
            elif url.path == "/suggest":
                params = parse_qs(url.query)
                only_path = (params.get("path") or [None])[0]
                self._send_json(get_suggestions(only_path=only_path))
            else:
                self._send_json({"error": "Not found."}, status=404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception:
            self._send_json({"error": "Internal server error."}, status=500)

    def do_POST(self):
        handler = {
            "/rename": self._post_rename,
            "/merge": self._post_merge,
            "/delete": self._post_delete,
        }.get(self.path)
        if handler is None:
            self._send_json({"error": "Not found."}, status=404)
            return
        try:
            data = self._read_json_body()
            handler(data)
        except json.JSONDecodeError:
            # Must come before ValueError (it is a subclass).
            self._send_json({"error": "Invalid JSON body."}, status=400)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception:
            self._send_json({"error": "Internal server error."}, status=500)

    def _post_rename(self, data):
        try:
            category_id = int(data.get("id"))
        except (TypeError, ValueError):
            raise ValueError("id must be an integer.")
        result = rename_category(category_id, data.get("new_path"))
        self._send_json({"success": True, **result})

    def _post_merge(self, data):
        try:
            source_id = int(data.get("source_id"))
            target_id = int(data.get("target_id"))
        except (TypeError, ValueError):
            raise ValueError("source_id and target_id must be integers.")
        result = merge_categories(source_id, target_id, data.get("new_name"))
        self._send_json({"success": True, **result})

    def _post_delete(self, data):
        try:
            category_id = int(data.get("id"))
        except (TypeError, ValueError):
            raise ValueError("id must be an integer.")
        result = delete_category(category_id)
        self._send_json({"success": True, **result})

    def log_request(self, code="-", size="-"):
        # Keep the console quiet for normal requests (match sibling tools'
        # low-noise feel); connection/protocol errors still go to stderr.
        pass


if __name__ == "__main__":
    host = os.environ.get("CATEGORY_EDITOR_HOST", "127.0.0.1")
    server = HTTPServer((host, PORT), EditorHandler)
    print(f"Category editor running at http://{host}:{PORT}")
    if host == "127.0.0.1":
        webbrowser.open(f"http://{host}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
