"""fzf-compatible fuzzy matching for tab completion (stdlib only).

This is a Python port of the scoring used by `fzf <https://github.com/junegunn/fzf>`_
(``src/algo/algo.go``, MIT licensed, © Junegunn Choi) so DailyDriver's
completion ranks and filters exactly the way fzf — and therefore fzf-tab —
does. That matters because fzf-tab only re-filters what the shell hook hands
it: a stricter matcher here would silently hide candidates fzf would have
shown (``da st1 rss<TAB>`` used to find nothing for that reason).

Rules implemented (single search term, default scoring scheme):

- **Fuzzy match** (``foo``): any in-order subsequence matches. There is no gap
  limit; gaps only cost score.
- **Scoring** (FuzzyMatchV2, a modified Smith-Waterman): +16 per matched
  character; -3 to open a gap and -1 per extra gap character; bonuses for
  matching at the start of a word (+8; +9 after ``/ , : ; |``; +10 after
  whitespace or at the start), at camelCase / letter-digit transitions (+7), and
  for consecutive runs (at least +4). The first query character's bonus is
  doubled.
- **Ordering**: higher score first, then shorter candidate, then original order
  (fzf's default ``--tiebreak=length``; ``tiebreak="index"`` skips the length rule).
- **Operators** inside the single word (spaces end a completion word, so fzf's
  AND / OR terms cannot occur): ``'foo`` exact substring, ``'foo'`` exact at
  word boundaries, ``^foo`` prefix, ``foo$`` suffix, ``^foo$`` whole string,
  ``!foo`` / ``!^foo`` / ``!foo$`` / ``!'foo`` (inverse fuzzy) exclude.
- Latin accents in candidates are folded (``é`` matches ``e``) like fzf's
  default normalisation, but only while the query itself is plain ASCII; a
  query containing an accent matches literally, as in fzf.

One deliberate difference: matching is always case-insensitive. fzf's
smart-case turns case-sensitive once the query has an uppercase letter; here
``Rel`` still finds ``relatives``, which also keeps this filter a superset of
what fzf will accept afterwards.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

# ── Scoring constants (verbatim from fzf's algo.go, default scheme) ───────

_SCORE_MATCH = 16
_SCORE_GAP_START = -3
_SCORE_GAP_EXTENSION = -1
_BONUS_BOUNDARY = _SCORE_MATCH // 2
_BONUS_NON_WORD = _SCORE_MATCH // 2
_BONUS_CAMEL123 = _BONUS_BOUNDARY + _SCORE_GAP_EXTENSION
_BONUS_CONSECUTIVE = -(_SCORE_GAP_START + _SCORE_GAP_EXTENSION)
_BONUS_FIRST_CHAR_MULTIPLIER = 2
_BONUS_BOUNDARY_WHITE = _BONUS_BOUNDARY + 2
_BONUS_BOUNDARY_DELIMITER = _BONUS_BOUNDARY + 1

_WHITE, _NON_WORD, _DELIMITER, _LOWER, _UPPER, _LETTER, _NUMBER = range(7)
_DELIMITER_CHARS = "/,:;|"
_WHITE_CHARS = " \t\n\v\f\r\x85\xa0"
# fzf's default scheme starts a string as if it followed whitespace.
_INITIAL_CLASS = _WHITE


def _ascii_class(char: str) -> int:
    if "a" <= char <= "z":
        return _LOWER
    if "A" <= char <= "Z":
        return _UPPER
    if "0" <= char <= "9":
        return _NUMBER
    if char in _WHITE_CHARS:
        return _WHITE
    if char in _DELIMITER_CHARS:
        return _DELIMITER
    return _NON_WORD


_ASCII_CLASSES = tuple(_ascii_class(chr(code)) for code in range(128))


def _char_class(char: str) -> int:
    code = ord(char)
    if code < 128:
        return _ASCII_CLASSES[code]
    category = unicodedata.category(char)
    if category == "Ll":
        return _LOWER
    if category == "Lu":
        return _UPPER
    if category[0] == "N":
        return _NUMBER
    if category[0] == "L":
        return _LETTER
    if char.isspace():
        return _WHITE
    return _NON_WORD


def _bonus_for(previous: int, current: int) -> int:
    if current >= _NON_WORD:
        if previous == _WHITE:
            return _BONUS_BOUNDARY_WHITE
        if previous == _DELIMITER:
            return _BONUS_BOUNDARY_DELIMITER
        if previous == _NON_WORD:
            return _BONUS_BOUNDARY
    if (previous == _LOWER and current == _UPPER) or (previous != _NUMBER and current == _NUMBER):
        return _BONUS_CAMEL123
    if current in (_NON_WORD, _DELIMITER):
        return _BONUS_NON_WORD
    if current == _WHITE:
        return _BONUS_BOUNDARY_WHITE
    return 0


_BONUS_MATRIX = tuple(tuple(_bonus_for(prev, cur) for cur in range(7)) for prev in range(7))

# ── Text preparation ─────────────────────────────────────────────────────


def _fold(char: str, strip_accents: bool) -> str:
    """Lowercase *char*, and strip a Latin accent when *strip_accents* is set."""
    lowered = char.lower()
    if len(lowered) != 1:
        lowered = char
    code = ord(lowered)
    if strip_accents and (0xC0 <= code <= 0x24F or 0x1E00 <= code <= 0x1EFF):
        decomposed = unicodedata.normalize("NFD", lowered)
        if decomposed and ord(decomposed[0]) < 0x250:
            return decomposed[0]
    return lowered


def _fold_text(text: str, strip_accents: bool = True) -> str:
    if text.isascii():
        return text.lower()
    return "".join(_fold(char, strip_accents) for char in text)


def _classes(text: str) -> list[int]:
    """Character class of every character of the *original* (un-folded) text."""
    if text.isascii():
        return [_ASCII_CLASSES[ord(char)] for char in text]
    return [_char_class(char) for char in text]


def _bonuses(classes: list[int]) -> list[int]:
    previous = _INITIAL_CLASS
    bonuses = []
    for current in classes:
        bonuses.append(_BONUS_MATRIX[previous][current])
        previous = current
    return bonuses


# ── Fuzzy match (FuzzyMatchV2) ───────────────────────────────────────────


def _fuzzy_match_score(text: str, pattern: str, classes: list[int]) -> int | None:
    """Best alignment score of *pattern* as a subsequence of *text*, or ``None``.

    *text* and *pattern* are already folded to lowercase; *classes* describes
    the original text.
    """
    size, length = len(text), len(pattern)
    if length > size:
        return None

    # Cheap in-order prefilter at C speed: most candidates die here.
    cursor = -1
    for char in pattern:
        cursor = text.find(char, cursor + 1)
        if cursor == -1:
            return None

    bonus = _bonuses(classes)
    first_char = pattern[0]

    if length == 1:
        best = 0
        for index, char in enumerate(text):
            if char != first_char:
                continue
            score = _SCORE_MATCH + bonus[index] * _BONUS_FIRST_CHAR_MULTIPLIER
            if score > best:
                best = score
                if bonus[index] >= _BONUS_BOUNDARY:
                    break
        return best

    # Phase 2: first occurrence of each pattern character, and the last
    # occurrence of the final one bounds the search window.
    first_positions: list[int] = []
    last_index = 0
    wanted = first_char
    for index, char in enumerate(text):
        if char == wanted:
            if len(first_positions) < length:
                first_positions.append(index)
                wanted = pattern[min(len(first_positions), length - 1)]
            last_index = index
    if len(first_positions) != length:
        return None

    start = first_positions[0]
    width = last_index - start + 1

    # Row 0: score of ending the first pattern character at each column.
    h_rows: list[list[int]] = [[0] * width for _ in range(length)]
    c_rows: list[list[int]] = [[0] * width for _ in range(length)]
    previous = 0
    in_gap = False
    for column in range(width):
        index = start + column
        if text[index] == first_char:
            current = _SCORE_MATCH + bonus[index] * _BONUS_FIRST_CHAR_MULTIPLIER
            c_rows[0][column] = 1
            in_gap = False
        else:
            current = max(previous + (_SCORE_GAP_EXTENSION if in_gap else _SCORE_GAP_START), 0)
            in_gap = True
        h_rows[0][column] = current
        previous = current

    # Rows 1..M-1: omission or mismatch of a pattern character is not allowed.
    best = 0
    for row in range(1, length):
        pattern_char = pattern[row]
        row_start = first_positions[row]
        h_row, c_row = h_rows[row], c_rows[row]
        h_above, c_above = h_rows[row - 1], c_rows[row - 1]
        in_gap = False
        for index in range(row_start, last_index + 1):
            column = index - start
            left = h_row[column - 1] if index > row_start else 0
            skip = left + (_SCORE_GAP_EXTENSION if in_gap else _SCORE_GAP_START)
            take = 0
            consecutive = 0
            if text[index] == pattern_char:
                take = h_above[column - 1] + _SCORE_MATCH
                point = bonus[index]
                consecutive = c_above[column - 1] + 1
                if consecutive > 1:
                    first_bonus = bonus[index - consecutive + 1]
                    if point >= _BONUS_BOUNDARY and point > first_bonus:
                        consecutive = 1  # a boundary starts a new chunk
                    else:
                        point = max(point, _BONUS_CONSECUTIVE, first_bonus)
                if take + point < skip:
                    take += bonus[index]
                    consecutive = 0
                else:
                    take += point
            c_row[column] = consecutive
            in_gap = take < skip
            score = max(take, skip, 0)
            if row == length - 1 and score > best:
                best = score
            h_row[column] = score
    return best


# ── Exact / prefix / suffix / equal matches ──────────────────────────────


def _score_span(text: str, pattern: str, classes: list[int], start: int, end: int) -> int:
    """fzf's ``calculateScore`` for the contiguous span ``text[start:end]``."""
    score = 0
    pattern_index = 0
    in_gap = False
    consecutive = 0
    first_bonus = 0
    previous = _INITIAL_CLASS if start == 0 else classes[start - 1]
    for index in range(start, end):
        current = classes[index]
        if text[index] == pattern[pattern_index]:
            score += _SCORE_MATCH
            point = _BONUS_MATRIX[previous][current]
            if consecutive == 0:
                first_bonus = point
            else:
                if point >= _BONUS_BOUNDARY and point > first_bonus:
                    first_bonus = point
                point = max(point, first_bonus, _BONUS_CONSECUTIVE)
            score += point * _BONUS_FIRST_CHAR_MULTIPLIER if pattern_index == 0 else point
            in_gap = False
            consecutive += 1
            pattern_index += 1
        else:
            score += _SCORE_GAP_EXTENSION if in_gap else _SCORE_GAP_START
            in_gap = True
            consecutive = 0
            first_bonus = 0
        previous = current
    return score


def _exact_score(text: str, pattern: str, classes: list[int], boundary: bool) -> int | None:
    """``'foo`` (substring, best bonus wins) or ``'foo'`` (word-boundary only)."""
    length = len(pattern)
    if len(text) < length:
        return None
    best_start = -1
    best_bonus = -1
    last_bonus = 0
    start = text.find(pattern)
    while start != -1:
        end = start + length
        point = _BONUS_BOUNDARY_WHITE if start == 0 else _BONUS_MATRIX[classes[start - 1]][classes[start]]
        if boundary:
            ok = point >= _BONUS_BOUNDARY
            ok = ok and (start == 0 or classes[start - 1] <= _DELIMITER)
            ok = ok and (end == len(text) or classes[end] <= _DELIMITER)
            if ok:
                best_start, best_bonus, last_bonus = start, point, point
                break
        else:
            if point > best_bonus:
                best_start, best_bonus = start, point
            if point >= _BONUS_BOUNDARY:
                break
        start = text.find(pattern, start + 1)
    if best_start < 0:
        return None
    end = best_start + length
    if boundary:
        # Underscore boundaries rank below the other kinds of boundaries.
        score = last_bonus
        deduct = last_bonus - _BONUS_BOUNDARY + 1
        if best_start > 0 and text[best_start - 1] == "_":
            score -= deduct + 1
            deduct = 1
        if end < len(text) and text[end] == "_":
            score -= deduct
        return score + _SCORE_MATCH * length + _BONUS_BOUNDARY_WHITE * (length + 1)
    return _score_span(text, pattern, classes, best_start, end)


def _prefix_score(text: str, pattern: str, classes: list[int]) -> int | None:
    trimmed = len(text) - len(text.lstrip(_WHITE_CHARS))
    if not text.startswith(pattern, trimmed):
        return None
    return _score_span(text, pattern, classes, trimmed, trimmed + len(pattern))


def _suffix_score(text: str, pattern: str, classes: list[int]) -> int | None:
    trimmed = len(text.rstrip(_WHITE_CHARS))
    if trimmed < len(pattern) or not text.startswith(pattern, trimmed - len(pattern)):
        return None
    return _score_span(text, pattern, classes, trimmed - len(pattern), trimmed)


def _equal_score(text: str, pattern: str) -> int | None:
    if text.strip(_WHITE_CHARS) != pattern:
        return None
    length = len(pattern)
    return (_SCORE_MATCH + _BONUS_BOUNDARY_WHITE) * length + (_BONUS_FIRST_CHAR_MULTIPLIER - 1) * _BONUS_BOUNDARY_WHITE


# ── Query parsing and ranking ────────────────────────────────────────────

_FUZZY, _EXACT, _EXACT_BOUNDARY, _PREFIX, _SUFFIX, _EQUAL = range(6)


class _Term:
    """One parsed search term: a match kind, a folded pattern, and inversion."""

    __slots__ = ("inverse", "kind", "pattern", "strip_accents")

    def __init__(self, kind: int, pattern: str, inverse: bool, strip_accents: bool):
        self.kind = kind
        self.pattern = pattern
        self.inverse = inverse
        # fzf folds accents in the candidates only while the query is plain
        # ASCII; a query with an accent in it matches literally.
        self.strip_accents = strip_accents

    def score(self, candidate: str) -> int | None:
        """Score *candidate* (higher is better) or ``None`` when it does not match."""
        text = _fold_text(candidate, self.strip_accents)
        kind = self.kind
        if kind == _EQUAL:
            result = _equal_score(text, self.pattern)
        elif kind == _FUZZY:
            result = _fuzzy_match_score(text, self.pattern, _classes(candidate))
        elif kind == _PREFIX:
            result = _prefix_score(text, self.pattern, _classes(candidate))
        elif kind == _SUFFIX:
            result = _suffix_score(text, self.pattern, _classes(candidate))
        else:
            result = _exact_score(text, self.pattern, _classes(candidate), kind == _EXACT_BOUNDARY)
        if self.inverse:
            return 0 if result is None else None
        return result


def parse_term(word: str) -> _Term | None:
    """Parse one completion word into a term, or ``None`` when it matches everything.

    Mirrors fzf's term parser for a single token: a leading ``!`` inverts an
    exact match, a trailing ``$`` makes a suffix match, ``'x'`` is a boundary
    match, a leading ``'`` an exact match, and a leading ``^`` a prefix match
    (or whole-string match together with ``$``). An operator with nothing after
    it matches everything.
    """
    text = word
    kind = _FUZZY
    inverse = False
    if text.startswith("!"):
        inverse = True
        kind = _EXACT
        text = text[1:]
    if text != "$" and text.endswith("$"):
        kind = _SUFFIX
        text = text[:-1]
    if len(text) > 2 and text.startswith("'") and text.endswith("'"):
        kind = _EXACT_BOUNDARY
        text = text[1:-1]
    elif text.startswith("'"):
        # A leading quote flips exactness: exact in the default fuzzy mode,
        # fuzzy after ``!`` (``!'foo`` is an inverse *fuzzy* match).
        kind = _FUZZY if inverse else _EXACT
        text = text[1:]
    elif text.startswith("^"):
        kind = _EQUAL if kind == _SUFFIX else _PREFIX
        text = text[1:]
    if text == "":
        return None
    strip_accents = word.isascii()
    return _Term(kind, _fold_text(text, strip_accents), inverse, strip_accents)


def rank_matches(candidates: Sequence[str], word: str, tiebreak: str = "length") -> list[str]:
    """Filter and order *candidates* by *word* the way fzf does.

    Best score first. Ties go to the shorter candidate, then to the incoming
    order (fzf's default ``--tiebreak=length``); pass ``tiebreak="index"`` to
    let the incoming order alone break ties, for lists that arrive already
    ranked by relevance. Duplicates are dropped, and an empty (or
    operator-only) word keeps everything in the incoming order, as does an
    exclusion-only ``!foo`` word.
    """
    unique = list(dict.fromkeys(candidates))
    term = parse_term(word)
    if term is None:
        return unique
    if term.inverse:
        # fzf does not sort a query made only of inverse terms.
        return [candidate for candidate in unique if term.score(candidate) is not None]
    ranked: list[tuple[int, int, int, str]] = []
    for index, candidate in enumerate(unique):
        score = term.score(candidate)
        if score is not None:
            tie = len(candidate.strip()) if tiebreak == "length" else 0
            ranked.append((-score, tie, index, candidate))
    ranked.sort()
    return [candidate for _, _, _, candidate in ranked]
