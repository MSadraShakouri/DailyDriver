"""Full‑text search for journal entries using SQLite FTS5."""
import sqlite3
from dailydriver.core.database import get_connection_cm
from dailydriver.core.keyword_learner import tokenize
from dailydriver.ui.terminal_ui import current_ui

def _build_query(text):
    """Convert free text to an FTS5 query.
    Returns (fts_query_string, display_terms) or (None, None) if no tokens.
    fts_query uses each stemmed token suffixed with '*' for prefix matching.
    """
    tokens = tokenize(text, stem_words=True)
    if not tokens:
        return None, None
    # Join with AND so that all terms must be present, improving precision
    fts_query = " AND ".join(tok + "*" for tok in tokens)
    display_terms = " ".join(tokens)
    return fts_query, display_terms

def search(cmd):
    """Usage: search <terms>  – full-text search across journal descriptions."""
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        current_ui.print_line("Usage: search <terms>  (e.g. search sadra well-known)")
        return None

    fts_query, display_terms = _build_query(parts[1])
    if fts_query is None:
        current_ui.print_line("No valid search terms (need at least one word).")
        return None

    page_size = 10
    offset = 0

    with get_connection_cm() as conn:
        cur = conn.cursor()

        while True:
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
                LIMIT ? OFFSET ?
            """, (fts_query, page_size, offset))
            rows = cur.fetchall()

            if not rows and offset == 0:
                current_ui.print_line("No matching entries found.")
                return

            current_ui.clear()
            current_ui.print_line(f"🔍 Search results for: {display_terms}")
            current_ui.print_line("─" * 40)
            for row in rows:
                # Convert created_at to Jalali date/time
                from datetime import datetime
                import jdatetime
                dt = datetime.fromtimestamp(row['created_at'])
                jdt = jdatetime.datetime.fromtimestamp(row['created_at'])
                date_str = jdt.strftime('%Y-%m-%d %H:%M')
                # Show first 100 chars of description as a preview
                desc_preview = (row['description'] or '')[:100].replace('\n', ' ')
                current_ui.print_line(f"[{row['id']:4d}] {date_str}  {row['categories']}  "
                                      f"(relevance {row['relevance']:.3f})")
                current_ui.print_line(f"      {desc_preview}")
                current_ui.print_line()

            current_ui.print_line("(n)ext  (p)rev  (q)uit  [id] view")
            choice = current_ui.prompt("> ").strip().lower()

            if choice == 'q':
                break
            elif choice == 'n':
                if len(rows) == page_size:
                    offset += page_size
                else:
                    current_ui.print_line("No more results.")
                    current_ui.prompt()
            elif choice == 'p':
                offset = max(0, offset - page_size)
            elif choice.isdigit():
                # Reuse the existing entry viewer for convenience
                from dailydriver.cli.entry_viewer import edit_entry
                from dailydriver.core.logger import log_free_text
                entry_id = int(choice)
                new_desc = edit_entry(entry_id)
                if new_desc is not None:
                    log_free_text(new_desc)
                    # After editing, the search needs to be re‑opened; just return.
                    return
            else:
                current_ui.print_line("Unknown option.")
                current_ui.prompt()
