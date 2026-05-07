# dailydriver/cli/search_view.py
"""Full‑text search with FTS5, LIKE fallback, and fuzzy time/date/category boosting."""
import sqlite3
from dailydriver.core.database import get_connection_cm
from dailydriver.core.keyword_learner import tokenize
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.cli.search.scoring import compute_final_scores

def _get_jalali_date(ts):
    import jdatetime
    jdt = jdatetime.datetime.fromtimestamp(ts)
    return jdt.strftime('%Y-%m-%d %H:%M')

def search(cmd):
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        current_ui.print_line("Usage: search <terms>")
        return None

    raw_tokens = tokenize(parts[1], stem_words=False)
    stemmed_tokens = tokenize(parts[1], stem_words=True)

    if not raw_tokens:
        current_ui.print_line("No valid search terms (need at least one word).")
        return None

    fts_query = " OR ".join(tok + "*" for tok in stemmed_tokens)
    page_size = 10
    offset = 0

    with get_connection_cm() as conn:
        cur = conn.cursor()

        all_rows = []          # merged before final scoring
        seen_ids = set()

        # ----- FTS5 search (descriptions) -----
        try:
            cur.execute("""
                SELECT e.id, e.description, e.created_at, e.started_at,
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
                if row['id'] not in seen_ids:
                    seen_ids.add(row['id'])
                    all_rows.append(dict(row))
        except sqlite3.OperationalError:
            pass

        # ----- LIKE fallback on descriptions -----
        if stemmed_tokens:
            like_clauses = " OR ".join("e.description LIKE ?" for _ in stemmed_tokens)
            like_params = [f"%{t}%" for t in stemmed_tokens]
            try:
                cur.execute(f"""
                    SELECT e.id, e.description, e.created_at, e.started_at,
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
                    if row['id'] not in seen_ids:
                        seen_ids.add(row['id'])
                        all_rows.append(dict(row))
            except sqlite3.OperationalError:
                pass

        # ----- Category path LIKE search (using raw tokens) -----
        if raw_tokens:
            cat_clauses = " OR ".join("c.path LIKE ?" for _ in raw_tokens)
            cat_params = [f"%{t}%" for t in raw_tokens]
            try:
                cur.execute(f"""
                    SELECT e.id, e.description, e.created_at, e.started_at,
                           COALESCE(GROUP_CONCAT(c.path, ', '), '(no category)') as categories,
                           NULL as relevance
                    FROM entries e
                    JOIN entry_categories ec ON e.id = ec.entry_id
                    JOIN categories c ON ec.category_id = c.id
                    WHERE {cat_clauses}
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                """, cat_params)
                for row in cur.fetchall():
                    if row['id'] not in seen_ids:
                        seen_ids.add(row['id'])
                        # Mark these as category-only matches (still scored)
                        record = dict(row)
                        record['relevance'] = None  # no FTS rank
                        all_rows.append(record)
            except sqlite3.OperationalError:
                pass

        # ----- final scoring (using raw_tokens for fuzzy boosts) -----
        all_rows = compute_final_scores(all_rows, [], raw_tokens, stemmed_tokens)

        total = len(all_rows)

        if total == 0:
            current_ui.print_line("No matching entries found.")
            return

        # Paginate (same as before)
        while True:
            page = all_rows[offset:offset + page_size]
            if not page and offset == 0:
                current_ui.print_line("No matching entries found.")
                return

            current_ui.clear()
            display_terms = " ".join(raw_tokens)
            current_ui.print_line(f"🔍 Search results for: {display_terms}")
            current_ui.print_line("─" * 40)
            for row in page:
                date_str = _get_jalali_date(row['created_at'])
                fts_rel = row.get('relevance')
                if fts_rel is not None:
                    rel_str = f"(FTS {fts_rel:.3f}, final {row['final_score']:.3f})"
                else:
                    rel_str = f"(cat match, final {row['final_score']:.3f})"
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
