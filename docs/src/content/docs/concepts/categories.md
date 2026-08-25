---
title: "Categories & Keyword Learning"
---

Journal entries are filed under category **paths** like `work/coding` or
`hygiene/shaving`. DailyDriver learns which words go with which categories, so
over time it suggests the right ones automatically.

## How suggestions are ranked

When you write an entry, the text is tokenized (lowercased, stripped of
punctuation, short and stop words removed, and stemmed with a Porter2 stemmer).
Each remaining token contributes to a category's score in two stages:

### 1. TF-IDF over learned keywords

Every time you file an entry under a category, its words are recorded as
keywords for that category with a count. When scoring a new entry, each token
adds `tf × idf`:

- **tf** — how often that word has been associated with the category.
- **idf** — `log(total_categories / (df + 1))`, clamped at 0 so a word that
  appears in almost every category never subtracts from a score. Words that are
  distinctive to a few categories carry more weight.

### 2. Gentle exact-match boost

A category whose **path** contains one of your words is usually the right
bucket. Matching is done on whole path *segments* (the path is split on `/` and
non-alphabetic characters and stemmed), so `art` matches `art/painting` but not
`start/routine`, and `log` matches `log/system` but not `blog/writing`.

Because such a category almost always *also* has that word as a learned keyword,
it already earns TF-IDF credit for the match — so the boost is a gentle
tiebreaker, not a sledgehammer. It is a small fraction of the strongest TF-IDF
score in the query (`EXACT_MATCH_RELATIVE`, with an `EXACT_MATCH_FLOOR` for fresh
databases), and it is shaped two ways:

- **Coverage-proportional** — scaled by the fraction of the path's segments the
  query matches, so a single-segment partial match of a deep path gets only a
  small bump.
- **Full-match bonus** — when the query covers *all* of a path's segments, it
  earns an extra `FULL_MATCH_BONUS`, so a full exact match reliably outranks a
  deeper partial one (e.g. `free_learning` beats `free_learning/art` for the
  query "learning").

Results are returned already ordered. The short numbered list shows the top
`MAX_RESULTS` (default 5); the rich dropdown asks for more (`DROPDOWN_RANKED`,
default 20) so its live completions stay relevance-ordered well past the
numbered list, after which the remaining catalog follows alphabetically. All the
tuning constants (`EXACT_MATCH_RELATIVE`, `EXACT_MATCH_FLOOR`,
`FULL_MATCH_BONUS`, `MIN_SCORE`, `MAX_RESULTS`, `DROPDOWN_RANKED`) live at the
top of `dailydriver/core/journal/keywords.py`.

## Selecting categories

A short numbered list of the top suggestions is shown in ranked order. On an
interactive terminal the picker also autocompletes as you type, with a live
dropdown ordered by relevance (the ranked list first, then the rest of your
catalog alphabetically):

- **Enter** alone always accepts suggestion **#1**, regardless of whether a
  great event is active.
- Type **numbers** (space-separated) to pick several from the visible numbered
  list.
- Type a **new path** to create it on the spot; multiple space-separated paths
  are all applied.
- **`0`** is the explicit opt-in for "Great Event only" when a great event is
  active (a convenient fallback when you don't want #1 and don't want to type
  the full event category).

The live dropdown drops entries you've already committed on the line — by path,
or by number (typing `3` removes the third suggestion) — and selecting the same
category twice (e.g. by number and by name) is collapsed to one.

On non-interactive input (piped, redirected) it falls back to the classic
numbered prompt with the same options.

## Learning

After you file an entry, its words are recorded (or their counts incremented)
for each chosen category, so future suggestions improve. This is why the same
kind of entry gets easier to categorize the more you use the app.
