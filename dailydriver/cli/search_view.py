# dailydriver/cli/search_view.py
"""Full‑text search with FTS5, LIKE fallback, and fuzzy time/date/category boosting."""

import re
import sqlite3

import jdatetime

from dailydriver.cli.entry_viewer import edit_entry
from dailydriver.cli.search.scoring import compute_final_scores
from dailydriver.core.database import get_connection_cm
from dailydriver.core.journal import log_free_text, tokenize
from dailydriver.display.display_utils import pline_wrap, wrap_line
from dailydriver.ui.terminal_ui import current_ui


def _get_jalali_date(ts):
    jdt = jdatetime.datetime.fromtimestamp(ts)
    return jdt.strftime("%Y-%m-%d %H:%M")


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

        all_rows = []  # merged before final scoring
        seen_ids = set()

        # ----- FTS5 search (descriptions) -----
        try:
            cur.execute(
                """
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
            """,
                (fts_query,),
            )
            for row in cur.fetchall():
                if row["id"] not in seen_ids:
                    seen_ids.add(row["id"])
                    all_rows.append(dict(row))
        except sqlite3.OperationalError:
            pass

        # ----- LIKE fallback on descriptions -----
        if stemmed_tokens:
            like_clauses = " OR ".join("e.description LIKE ?" for _ in stemmed_tokens)
            like_params = [f"%{t}%" for t in stemmed_tokens]
            try:
                cur.execute(
                    f"""
                    SELECT e.id, e.description, e.created_at, e.started_at,
                           COALESCE(GROUP_CONCAT(c.path, ', '), '(no category)') as categories,
                           NULL as relevance
                    FROM entries e
                    LEFT JOIN entry_categories ec ON e.id = ec.entry_id
                    LEFT JOIN categories c ON ec.category_id = c.id
                    WHERE {like_clauses}
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                """,
                    like_params,
                )
                for row in cur.fetchall():
                    if row["id"] not in seen_ids:
                        seen_ids.add(row["id"])
                        all_rows.append(dict(row))
            except sqlite3.OperationalError:
                pass

        # ----- Category path LIKE search (using raw tokens) -----
        if raw_tokens:
            cat_clauses = " OR ".join("c.path LIKE ?" for _ in raw_tokens)
            cat_params = [f"%{t}%" for t in raw_tokens]
            try:
                cur.execute(
                    f"""
                    SELECT e.id, e.description, e.created_at, e.started_at,
                           COALESCE(GROUP_CONCAT(c.path, ', '), '(no category)') as categories,
                           NULL as relevance
                    FROM entries e
                    JOIN entry_categories ec ON e.id = ec.entry_id
                    JOIN categories c ON ec.category_id = c.id
                    WHERE {cat_clauses}
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                """,
                    cat_params,
                )
                for row in cur.fetchall():
                    if row["id"] not in seen_ids:
                        seen_ids.add(row["id"])
                        # Mark these as category-only matches (still scored)
                        record = dict(row)
                        record["relevance"] = None  # no FTS rank
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
            page = all_rows[offset : offset + page_size]
            if not page and offset == 0:
                current_ui.print_line("No matching entries found.")
                return

            current_ui.clear()
            display_terms = " ".join(raw_tokens)
            current_ui.print_line(f"🔍 Search results for: {display_terms}")
            current_ui.print_line("─" * 40)
            for row in page:
                date_str = _get_jalali_date(row["created_at"])
                fts_rel = row.get("relevance")
                if fts_rel is not None:
                    rel_str = f"(FTS {fts_rel:.3f}, final {row['final_score']:.3f})"
                else:
                    rel_str = f"(cat match, final {row['final_score']:.3f})"
                desc_raw = (row["description"] or "").replace("\n", " ")
                # Highlight matching tokens using reverse video
                highlighted = desc_raw
                for token in stemmed_tokens:
                    pattern = re.compile(re.escape(token), re.IGNORECASE)
                    highlighted = pattern.sub(lambda m: f"\033[7m{m.group()}\033[0m", highlighted)
                # Header line: ID + date + relevance
                header_line = f"[{row['id']}] {date_str} {rel_str}"
                current_ui.print_line(header_line)

                # Categories: indented under the date line (same width as header prefix)
                cats = row["categories"] or "(no category)"
                cats_indent = " " * len(f"[{row['id']}] ")
                wrap_line(cats_indent, cats, cats_indent)

                # Description: 2‑space indent, up to 3 lines
                pline_wrap(highlighted, indent=2, max_lines=3)

                # Blank line between entries
                current_ui.print_line()

            current_ui.print_line(f"Showing {offset+1}‑{min(offset+page_size, total)} of {total}")
            current_ui.print_line("\n\033[1m(n)ext  (p)rev  (q)uit  [id] edit  (d)ay <id>\033[0m")
            current_ui.print_line("\033[1mn/p = next/prev page, 5n = 5 pages\033[0m")
            current_ui.print_line()
            choice = current_ui.prompt("> ").strip().lower()

            if choice == "q":
                break
            elif re.match(r"^\d*[np]$", choice):
                steps = int(choice[:-1]) if choice[:-1] else 1
                if choice[-1] == "n":
                    if offset + page_size < total:
                        offset += steps * page_size
                    else:
                        current_ui.print_line("No more results.")
                        current_ui.prompt("Press Enter to continue.")
                else:  # 'p'
                    if offset > 0:
                        offset = max(0, offset - steps * page_size)
                    else:
                        current_ui.print_line("Already on first page.")
                        current_ui.prompt("Press Enter to continue.")

            elif choice.startswith("d"):
                parts = choice.split(maxsplit=1)
                if len(parts) == 2:
                    eid = parts[1].strip()
                else:
                    eid = current_ui.prompt("Entry ID: ").strip()
                if eid.isdigit():
                    from dailydriver.cli.day_view import show_day

                    with get_connection_cm() as conn2:
                        cur2 = conn2.cursor()
                        cur2.execute("SELECT created_at FROM entries WHERE id=?", (int(eid),))
                        row2 = cur2.fetchone()
                        if row2:
                            jd = jdatetime.datetime.fromtimestamp(row2["created_at"])
                            show_day(jd.strftime("%Y-%m-%d"))
                            return
                        else:
                            current_ui.print_line("Entry not found.")
                            current_ui.prompt("Press Enter to continue.")

            elif choice.isdigit():
                entry_id = int(choice)
                new_desc = edit_entry(entry_id)
                if new_desc is not None:
                    log_free_text(new_desc)
                    return
            else:
                current_ui.print_line("Unknown option.")
                current_ui.prompt("Press Enter to continue.")
