# dailydriver/cli/search_view.py
"""Full‑text search with FTS5 and LIKE fallback."""
import sqlite3
from dailydriver.core.database import get_connection_cm
from dailydriver.core.keyword_learner import tokenize
from dailydriver.ui.terminal_ui import current_ui

def _build_query(text):
    tokens = tokenize(text, stem_words=True)
    if not tokens:
        return None, None
    fts_query = " AND ".join(tok + "*" for tok in tokens)
    return fts_query, tokens

def search(cmd):
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        current_ui.print_line("Usage: search <terms>")
        return None

    fts_query, tokens = _build_query(parts[1])
    if fts_query is None:
        current_ui.print_line("No valid search terms (need at least one word).")
        return None

    page_size = 10
    offset = 0

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Collect results from FTS5
        fts_ids = set()
        fts_results = []  # list of dicts
        try:
            cur.execute("""
                SELECT e.id, e.description, e.created_at,
                       COALESCE(GROUP_CONCAT(c.path, ', '), '(no category)') as categories,
                       rank as relevance
                FROM entries_fts
                JOIN entries e ON e.id = entries_fts.rowid
                LEFT JOIN entry_categories ec ON e.id = ec.entry_id
                LEFT JOIN categories c ON ec.category_id = c.id
                WHERE entries_fts MATCH ?
                GROUP BY e.id
                ORDER BY rank
            """, (fts_query,))
            for row in cur.fetchall():
                fts_ids.add(row['id'])
                fts_results.append(dict(row))
        except sqlite3.OperationalError:
            pass  # if FTS query fails, continue to LIKE

        # LIKE fallback for substring matches
        like_results = []  # list of dicts
        if tokens:
            # Build multiple LIKE conditions with AND
            like_clauses = " AND ".join("e.description LIKE ?" for _ in tokens)
            like_params = [f"%{t}%" for t in tokens]
            try:
                cur.execute(f"""
                    SELECT e.id, e.description, e.created_at,
                           COALESCE(GROUP_CONCAT(c.path, ', '), '(no category)') as categories,
                           NULL as relevance
                    FROM entries e
                    LEFT JOIN entry_categories ec ON e.id = ec.entry_id
                    LEFT JOIN categories c ON ec.category_id = c.id
                    WHERE {like_clauses}
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                """, like_params)
                for row in cur.fetchall():
                    if row['id'] not in fts_ids:
                        like_results.append(dict(row))
                        fts_ids.add(row['id'])  # prevent duplicates
            except sqlite3.OperationalError:
                pass

        # Merge: FTS results first (ranked), then LIKE results (newest first)
        all_rows = fts_results + like_results
        total = len(all_rows)

        if total == 0:
            current_ui.print_line("No matching entries found.")
            return

        # Paginate manually
        while True:
            page = all_rows[offset:offset + page_size]
            if not page and offset == 0:
                current_ui.print_line("No matching entries found.")
                return

            current_ui.clear()
            display_terms = " ".join(tokens)
            current_ui.print_line(f"🔍 Search results for: {display_terms}")
            current_ui.print_line("─" * 40)
            for row in page:
                from datetime import datetime
                import jdatetime
                jdt = jdatetime.datetime.fromtimestamp(row['created_at'])
                date_str = jdt.strftime('%Y-%m-%d %H:%M')
                rel = row['relevance']
                rel_str = f"(relevance {rel:.3f})" if rel is not None else "(LIKE match)"
                desc_preview = (row['description'] or '')[:100].replace('\n', ' ')
                current_ui.print_line(f"[{row['id']:4d}] {date_str}  {row['categories']}  {rel_str}")
                current_ui.print_line(f"      {desc_preview}")
                current_ui.print_line()

            current_ui.print_line(f"Showing {offset+1}‑{min(offset+page_size, total)} of {total}")
            current_ui.print_line("(n)ext  (p)rev  (q)uit  [id] view")
            choice = current_ui.prompt("> ").strip().lower()

            if choice == 'q':
                break
            elif choice == 'n':
                if offset + page_size < total:
                    offset += page_size
                else:
                    current_ui.print_line("No more results.")
                    current_ui.prompt("Press Enter to continue.")
            elif choice == 'p':
                if offset > 0:
                    offset -= page_size
                else:
                    current_ui.print_line("Already on first page.")
                    current_ui.prompt("Press Enter to continue.")
            elif choice.isdigit():
                from dailydriver.cli.entry_viewer import edit_entry
                from dailydriver.core.logger import log_free_text
                entry_id = int(choice)
                new_desc = edit_entry(entry_id)
                if new_desc is not None:
                    log_free_text(new_desc)
                    return
            else:
                current_ui.print_line("Unknown option.")
                current_ui.prompt("Press Enter to continue.")
