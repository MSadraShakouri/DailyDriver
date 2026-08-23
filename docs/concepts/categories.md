# Categories & Keyword Learning

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

### 2. Relative exact-match boost

A category whose **path** contains one of your words is almost always the right
bucket. Matching is done on whole path *segments* (the path is split on `/` and
non-alphabetic characters and stemmed), so `art` matches `art/painting` but not
`start/routine`, and `log` matches `log/system` but not `blog/writing`.

Each exact segment match adds a boost scaled to the strongest TF-IDF score in
the current query (`EXACT_MATCH_RELATIVE`, with an `EXACT_MATCH_FLOOR` for fresh
databases where TF-IDF scores are tiny). Because the boost scales with the query,
an exact match reliably surfaces near the top (typically #1–#3) on any
database — even against a heavily trained but unrelated category — without being
hard-pinned to #1. Matching more segments of a path boosts it further.

The top matches (up to `MAX_RESULTS`, default 10) are returned already ordered.
These constants live at the top of
`dailydriver/core/journal/keywords.py` and are easy to tune.

## Selecting categories

The suggestions are shown in that ranked order. On an interactive terminal the
picker autocompletes as you type (ranked matches first, then the rest of your
catalog):

- **Enter** alone accepts the top-ranked suggestion.
- Type **numbers** (space-separated) to pick several from the list.
- Type a **new path** to create it on the spot; multiple space-separated paths
  are all applied.
- **`0`** selects "Great Event only" when a great event is active.

On non-interactive input (piped, redirected) it falls back to the classic
numbered prompt with the same options.

## Learning

After you file an entry, its words are recorded (or their counts incremented)
for each chosen category, so future suggestions improve. This is why the same
kind of entry gets easier to categorize the more you use the app.
