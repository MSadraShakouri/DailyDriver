# dailydriver/cli/search_view.py
"""Token-based journal search, grouped by how many query terms match.

No relevance scoring: search is a filter. Each query term is tokenized and
stemmed exactly like journal keywords; a term matches an entry when its stem
equals the stem of a whole word in the description or the category path
("art" never matches "start"). Results are grouped by match count — all N
terms first, then N-1, and so on — and sorted newest first (by start time)
within each group. The words that counted are the words highlighted.
"""

import re

from dailydriver.cli.entry_viewer import edit_entry, entry_time_display
from dailydriver.core.database import get_connection_cm
from dailydriver.core.journal import log_free_text, tokenize
from dailydriver.core.journal.keywords import path_segments
from dailydriver.display.display_utils import pline_wrap, wrap_line
from dailydriver.ui.terminal_ui import current_ui

_WORD_RE = re.compile(r"[a-zA-Z]+")
_HIGHLIGHT = "\033[7m{}\033[0m"

PAGE_SIZE = 10


def _stem(word: str) -> str:
    stemmed = tokenize(word, stem_words=True)
    return stemmed[0] if stemmed else word.lower()


def _query_terms(raw_query: str) -> tuple[list[str], list[str], list[str]]:
    """Return (display_terms, stemmed_terms, ignored_words) for a query.

    display_terms parallel stemmed_terms; words dropped by tokenization
    (too short, stopwords) are reported so "All N terms" stays honest.
    """
    display_terms: list[str] = []
    stemmed_terms: list[str] = []
    ignored: list[str] = []
    seen_stems: set[str] = set()
    seen_ignored: set[str] = set()
    for word in _WORD_RE.findall(raw_query.lower()):
        stems = tokenize(word, stem_words=True)
        if not stems:
            if word not in seen_ignored:
                seen_ignored.add(word)
                ignored.append(word)
            continue
        stem = stems[0]
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        stemmed_terms.append(stem)
        display_terms.append(word)
    return display_terms, stemmed_terms, ignored


def _entry_stems(description: str, categories: str) -> set[str]:
    """All comparable word stems of an entry: description words + path segments."""
    stems = set(tokenize(description or "", stem_words=True))
    for path in (categories or "").split(","):
        stems |= path_segments(path.strip())
    return stems


def _highlight_words(text: str, matched_stems: set[str]) -> str:
    """Reverse-video every whole word whose stem is a matched query term."""

    def replace(match: re.Match) -> str:
        word = match.group()
        return _HIGHLIGHT.format(word) if _stem(word) in matched_stems else word

    return _WORD_RE.sub(replace, text)


def _group_header(matched: int, total_terms: int, count: int) -> str:
    noun = "entry" if count == 1 else "entries"
    if total_terms == 1:
        label = "1 term"
    elif matched == total_terms:
        label = f"All {total_terms} terms"
    else:
        label = f"{matched} of {total_terms} terms"
    return f"── {label} ({count} {noun}) ──"


def search(cmd):
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        current_ui.print_line("Usage: search <terms>")
        return None

    display_terms, stemmed_terms, ignored = _query_terms(parts[1])
    if not stemmed_terms:
        current_ui.print_line("No valid search terms (need at least one word of 3+ letters).")
        return None

    total_terms = len(stemmed_terms)
    query_stems = set(stemmed_terms)

    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.id, e.description, e.created_at, e.started_at, e.duration_minutes,
                   COALESCE(GROUP_CONCAT(c.path, ', '), '') AS categories
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            GROUP BY e.id
            ORDER BY COALESCE(e.started_at, e.created_at) DESC
            """
        )
        rows = cur.fetchall()

    # Filter + annotate with matched terms. Rows stay newest-first.
    results = []
    for row in rows:
        matched = query_stems & _entry_stems(row["description"], row["categories"])
        if matched:
            results.append((len(matched), dict(row), matched))

    if not results:
        current_ui.print_line("No matching entries found.")
        return None

    # Group by match count, best groups first; order within groups preserved.
    group_sizes = {}
    for match_count, _, _ in results:
        group_sizes[match_count] = group_sizes.get(match_count, 0) + 1
    results.sort(key=lambda item: -item[0])

    total = len(results)
    offset = 0

    while True:
        page = results[offset : offset + PAGE_SIZE]
        current_ui.clear()
        header = f"🔍 Search: {' '.join(display_terms)}"
        if ignored:
            header += f"   (ignored: {', '.join(ignored)})"
        current_ui.print_line(header)
        current_ui.print_line("─" * 40)

        previous_count = results[offset - 1][0] if offset > 0 else None
        for index, (match_count, row, matched) in enumerate(page):
            if match_count != previous_count:
                # A group starts here: print its header inline.
                current_ui.print_line(_group_header(match_count, total_terms, group_sizes[match_count]))
            elif index == 0:
                # Page starts mid-group: repeat the header as a continuation.
                header_line = _group_header(match_count, total_terms, group_sizes[match_count])
                current_ui.print_line(header_line.replace(") ──", ", cont.) ──"))
            previous_count = match_count

            time_str = entry_time_display(row["started_at"], row["created_at"], row["duration_minutes"])
            current_ui.print_line(f"[{row['id']}] {time_str}")

            cats = row["categories"] or "(no category)"
            cats_indent = " " * len(f"[{row['id']}] ")
            wrap_line(cats_indent, _highlight_words(cats, matched), cats_indent)

            desc = (row["description"] or "").replace("\n", " ")
            if desc:
                pline_wrap(_highlight_words(desc, matched), indent=2, max_lines=3)
            current_ui.print_line()

        current_ui.print_line(f"Showing {offset + 1}‑{min(offset + PAGE_SIZE, total)} of {total}")
        current_ui.print_line("\n\033[1m(n)ext  (p)rev  (q)uit  [id] edit  (d)ay <id>\033[0m")
        current_ui.print_line("\033[1mn/p = next/prev page, 5n = 5 pages\033[0m")
        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif re.match(r"^\d*[np]$", choice):
            steps = int(choice[:-1]) if choice[:-1] else 1
            if choice[-1] == "n":
                if offset + PAGE_SIZE < total:
                    offset = min(offset + steps * PAGE_SIZE, ((total - 1) // PAGE_SIZE) * PAGE_SIZE)
                else:
                    current_ui.print_line("No more results.")
                    current_ui.prompt("Press Enter to continue.")
            else:  # 'p'
                if offset > 0:
                    offset = max(0, offset - steps * PAGE_SIZE)
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
                import jdatetime

                from dailydriver.cli.day_view import show_day

                with get_connection_cm() as conn2:
                    cur2 = conn2.cursor()
                    cur2.execute(
                        "SELECT COALESCE(started_at, created_at) AS ts FROM entries WHERE id=?",
                        (int(eid),),
                    )
                    row2 = cur2.fetchone()
                if row2:
                    jd = jdatetime.datetime.fromtimestamp(row2["ts"])
                    show_day(jd.strftime("%Y-%m-%d"))
                    return None
                current_ui.print_line("Entry not found.")
                current_ui.prompt("Press Enter to continue.")

        elif choice.isdigit():
            entry_id = int(choice)
            new_desc = edit_entry(entry_id)
            if new_desc is not None:
                log_free_text(new_desc)
                return None
        else:
            pass

    return None
