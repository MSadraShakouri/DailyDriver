"""A small, dependency-free Porter2-compatible English stemmer.

DailyDriver only needs the single-word ``stem`` operation from the former
``porter2stemmer`` dependency.  This module keeps the useful suffix rules
locally instead of pulling a third-party package into every installation.

The implementation follows the English Porter2/Snowball algorithm described by
Martin Porter.  It intentionally exposes a function rather than the old
package's stateful wrapper: region boundaries are recalculated for every word.
"""

from __future__ import annotations

_VOWELS = frozenset("aeiouy")
_DOUBLES = frozenset(("bb", "dd", "ff", "gg", "mm", "nn", "pp", "rr", "tt"))
_LI_ENDINGS = frozenset("cdeghkmnrt")

# The order is significant: each step applies the first matching suffix.
_STEP_2_REPLACEMENTS = (
    ("tional", "tion"),
    ("enci", "ence"),
    ("anci", "ance"),
    ("abli", "able"),
    ("entli", "ent"),
    ("izer", "ize"),
    ("ization", "ize"),
    ("ation", "ate"),
    ("ator", "ate"),
    ("alism", "al"),
    ("aliti", "al"),
    ("alli", "al"),
    ("fulness", "ful"),
    ("ousness", "ous"),
    ("ousli", "ous"),
    ("iveness", "ive"),
    ("iviti", "ive"),
    ("biliti", "ble"),
    ("bli", "ble"),
    ("fulli", "ful"),
    ("lessli", "less"),
)
_STEP_3_REPLACEMENTS = (
    ("ational", "ate"),
    ("tional", "tion"),
    ("alize", "al"),
    ("icate", "ic"),
    ("iciti", "ic"),
    ("ical", "ic"),
    ("ful", ""),
    ("ness", ""),
)
_STEP_4_SUFFIXES = (
    "ement",
    "ance",
    "ence",
    "able",
    "ible",
    "ment",
    "ant",
    "ent",
    "ism",
    "ate",
    "iti",
    "ous",
    "ive",
    "ize",
    "al",
    "er",
    "ic",
)


def _regions(word: str) -> tuple[int, int]:
    """Return the starts of R1 and R2, using ``len(word)`` for an empty region."""
    region_starts: list[int] = []
    for index in range(len(word) - 1):
        if word[index] in _VOWELS and word[index + 1] not in _VOWELS:
            # A vowel/consonant pair at the very end has no following region.
            if index + 2 < len(word):
                region_starts.append(index + 2)
                if len(region_starts) == 2:
                    break
    end = len(word)
    return (region_starts + [end, end])[:2]


def _short_word(word: str, r1: int) -> bool:
    """Whether *word* ends in a short syllable and has an empty R1."""
    if r1 < len(word):
        return False
    if len(word) > 2:
        return (
            word[-3] not in _VOWELS
            and word[-2] in _VOWELS
            and word[-1] not in frozenset("aeiouwxY")
        )
    return len(word) == 2 and word[0] in _VOWELS and word[1] not in _VOWELS


def _mark_ys(word: str) -> str:
    """Mark ``y`` characters that act as consonants with uppercase ``Y``."""
    chars = list(word)
    if chars and chars[0] == "y":
        chars[0] = "Y"
    for index in range(1, len(chars)):
        if chars[index] == "y" and chars[index - 1] in _VOWELS:
            chars[index] = "Y"
    return "".join(chars)


def _step_1a(word: str) -> str:
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith(("ied", "ies")):
        stem = word[:-3]
        return stem + ("ie" if len(stem) == 1 else "i")
    if word.endswith(("us", "ss")):
        return word
    if word.endswith("s") and any(char in _VOWELS for char in word[:-2]):
        return word[:-1]
    return word


def _step_1b(word: str, r1: int) -> str:
    if word.endswith("eedly"):
        if len(word) - 5 >= r1:
            return word[:-5] + "ee"
        return word
    if word.endswith("eed"):
        if len(word) - 3 >= r1:
            return word[:-3] + "ee"
        return word

    suffixes = ("ingly", "edly", "ing", "ed")
    for suffix in suffixes:
        if word.endswith(suffix) and any(char in _VOWELS for char in word[: -len(suffix)]):
            word = word[: -len(suffix)]
            break
    else:
        return word

    if word.endswith(("at", "bl", "iz")):
        return word + "e"
    if word[-2:] in _DOUBLES:
        return word[:-1]
    if _short_word(word, r1):
        return word + "e"
    return word


def _step_1c(word: str) -> str:
    if len(word) > 2 and word[-1] in "yY" and word[-2] not in _VOWELS:
        return word[:-1] + "i"
    return word


def _replace_in_region(word: str, suffix: str, replacement: str, r1: int) -> str:
    if word.endswith(suffix) and len(word) - len(suffix) >= r1:
        return word[: -len(suffix)] + replacement
    return word


def _step_2(word: str, r1: int) -> str:
    for suffix, replacement in _STEP_2_REPLACEMENTS:
        if word.endswith(suffix):
            return _replace_in_region(word, suffix, replacement, r1)

    if word.endswith("ogi") and len(word) > 3 and word[-4] == "l":
        return _replace_in_region(word, "ogi", "", r1)
    if word.endswith("li") and len(word) > 2 and word[-3] in _LI_ENDINGS:
        return _replace_in_region(word, "li", "", r1)
    return word


def _step_3(word: str, r1: int, r2: int) -> str:
    for suffix, replacement in _STEP_3_REPLACEMENTS:
        if word.endswith(suffix):
            return _replace_in_region(word, suffix, replacement, r1)
    if word.endswith("ative") and len(word) - 5 >= r2:
        return word[:-5]
    return word


def _step_4(word: str, r2: int) -> str:
    for suffix in _STEP_4_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= r2:
            return word[: -len(suffix)]
    if word.endswith("ion") and len(word) > 3 and len(word) - 3 >= r2 and word[-4] in "st":
        return word[:-3]
    return word


def stem(word: str) -> str:
    """Return the Porter2 stem of one English word.

    The caller normally supplies lowercase alphabetic tokens.  Apostrophes are
    handled because journal text may contain possessives; punctuation other
    than apostrophes is deliberately left to the tokenizer.
    """
    if len(word) <= 2:
        return word

    if word.startswith("'"):
        word = word[1:]
    word = _mark_ys(word)
    r1, r2 = _regions(word)

    if word.endswith("'s'"):
        word = word[:-3]
    elif word.endswith("'s"):
        word = word[:-2]
    elif word.endswith("'"):
        word = word[:-1]

    word = _step_1a(word)
    word = _step_1b(word, r1)
    word = _step_1c(word)
    word = _step_2(word, r1)
    word = _step_3(word, r1, r2)
    word = _step_4(word, r2)

    if word.endswith("e"):
        if r2 <= len(word) - 1 or (r1 <= len(word) - 1 and not _short_word(word[:-1], r1)):
            word = word[:-1]
    elif word.endswith("ll") and r2 <= len(word) - 1:
        word = word[:-1]

    return word.replace("Y", "y")


__all__ = ["stem"]
