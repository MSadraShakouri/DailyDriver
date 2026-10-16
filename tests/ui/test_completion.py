# tests/ui/test_completion.py
"""Tests for the context-aware REPL completion engine."""

import jdatetime
import pytest
from prompt_toolkit.document import Document

from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.core.database import get_connection_cm
from dailydriver.core.state import start_numbered_state
from dailydriver.features.qada.entries import add_entry as add_qada
from dailydriver.features.targets.entries import add_entry as add_target
from dailydriver.ui.completion import (
    ReplCompleter,
    clear_completion_cache,
    split_completion_line,
    suggest,
    suggest_for_text,
)


@pytest.fixture
def command_names():
    return sorted(make_dispatch().keys()) + [f"st{i}" for i in range(1, 10)]


@pytest.fixture(autouse=True)
def clean_cache(db_path):
    clear_completion_cache()
    yield
    clear_completion_cache()


def _seed_categories(*paths):
    with get_connection_cm(auto=False) as conn:
        for path in paths:
            conn.execute("INSERT INTO categories (path) VALUES (?)", (path,))
        conn.commit()


# ── Line splitting ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "tokens", "word"),
    [
        ("", [], ""),
        ("   ", [], ""),
        ("qa", [], "qa"),
        ("qada", [], "qada"),
        ("qada ", ["qada"], ""),
        ("qada l", ["qada"], "l"),
        ("qada log ", ["qada", "log"], ""),
        ("  travel  o", ["travel"], "o"),
    ],
)
def test_split_completion_line(text, tokens, word):
    assert split_completion_line(text) == (tokens, word)


# ── First-token completion ───────────────────────────────────────────


def test_first_token_matches_commands(command_names):
    assert "travel" in suggest([], "tr", command_names)
    assert "travel" in suggest([], "", command_names)
    assert "qada" in suggest([], "qa", command_names)


def test_first_token_is_case_insensitive(command_names):
    assert "travel" in suggest([], "TR", command_names)


def test_first_token_includes_repl_only_tokens(command_names):
    assert ":m" in suggest([], ":", command_names)
    assert "---" in suggest([], "-", command_names)


def test_first_token_includes_numbered_singletons(command_names):
    matched = suggest([], "st", command_names)
    assert "st1" in matched and "st9" in matched


def test_unknown_first_token_gives_no_arg_completion(command_names):
    # Unknown words are journal text — no suggestions after them.
    assert suggest(["breakfast"], "with", command_names) == []
    assert suggest(["breakfast"], "", command_names) == []


# ── Numbered et/ln extensions ──────────────────────────────────────────


def test_numbered_extensions_offer_active_slots_only(command_names, db_path):
    start_numbered_state(1, ["work/code"])
    start_numbered_state(3, ["rest/nap"])
    start_numbered_state(4, ["food/lunch"])
    matched = suggest([], "et3", command_names)
    assert "et31" in matched
    assert "et34" in matched
    # Already-used digits and inactive slots are not extended.
    assert "et33" not in matched
    assert "et32" not in matched
    assert "et39" not in matched


def test_numbered_extensions_cover_ln_too(command_names, db_path):
    start_numbered_state(2, ["work/code"])
    assert "ln21" not in suggest([], "ln2", command_names)  # 1 inactive
    start_numbered_state(1, ["rest/nap"])
    clear_completion_cache()  # providers cache briefly; drop it after mutating
    assert "ln21" in suggest([], "ln2", command_names)


def test_numbered_extensions_capped_at_four_digits(command_names, db_path):
    start_numbered_state(1, ["work/code"])
    assert suggest([], "et3124", command_names) == [] or "et31241" not in suggest([], "et3124", command_names)


# ── Universal help flags ─────────────────────────────────────────────


@pytest.mark.parametrize("command", ["travel", "qada", "ee", "v", "stats", "day"])
def test_every_command_offers_help_flags(command_names, command):
    assert command in command_names
    matched = suggest([command], "-", command_names)
    assert "-h" in matched and "--help" in matched


def test_help_flags_shown_on_empty_word(command_names):
    matched = suggest(["travel"], "", command_names)
    assert "-h" in matched and "--help" in matched


# ── Static subcommands & flags ─────────────────────────────────────────


def test_travel_subcommands(command_names):
    matched = suggest(["travel"], "", command_names)
    assert {"on", "off", "status"} <= set(matched)
    assert suggest(["travel"], "o", command_names) == ["on"] or "on" in suggest(["travel"], "o", command_names)
    # No further positionals once the subcommand is given.
    assert suggest(["travel", "on"], "", command_names) == ["-h", "--help"]


def test_daystart_hours(command_names):
    matched = suggest(["daystart"], "", command_names)
    assert "0" in matched and "4" in matched and "23" in matched
    assert len([m for m in matched if m.isdigit()]) == 24


def test_export_durations_and_formats(command_names):
    matched = suggest(["export"], "", command_names)
    assert {"all", "7d", "--txt", "--md"} <= set(matched)
    # Once a duration is given, only formats remain.
    remaining = suggest(["export", "7d"], "", command_names)
    assert "--txt" in remaining and "--md" in remaining
    assert "all" not in remaining
    # And vice versa.
    remaining = suggest(["export", "--txt"], "", command_names)
    assert "all" in remaining and "7d" in remaining


def test_vexport_durations_only(command_names):
    matched = suggest(["vexport"], "", command_names)
    assert {"all", "7d"} <= set(matched)
    assert "--txt" not in matched


def test_qada_subcommands(command_names):
    assert set(suggest(["qada"], "", command_names)) >= {"log", "fasting"}
    assert suggest(["qada", "fasting"], "", command_names) >= ["yes", "no"] or set(
        suggest(["qada", "fasting"], "", command_names)
    ) >= {"yes", "no"}


def test_qada_log_offers_slots(command_names, db_path):
    matched = suggest(["qada", "log"], "", command_names)
    assert {"fajr", "dhuhr_asr", "maghrib_isha"} <= set(matched)


def test_qada_log_offers_entry_names_and_ids(command_names, db_path):
    entry_id = add_qada("fajr-backlog", "prayer", slot="fajr")
    matched = suggest(["qada", "log"], "", command_names)
    assert "fajr-backlog" in matched
    assert str(entry_id) in matched


def test_targets_subcommands(command_names):
    for command in ("nazr", "habit", "targets"):
        matched = suggest([command], "", command_names)
        assert {"log", "daily_total", "counter_total", "counter_reset"} <= set(matched)


def test_targets_names_filtered_by_kind(command_names, db_path):
    add_target("nazr", "quran-pages")
    add_target("habit", "morning-walk")
    assert "quran-pages" in suggest(["nazr", "log"], "", command_names)
    assert "morning-walk" not in suggest(["nazr", "log"], "", command_names)
    assert "morning-walk" in suggest(["habit", "log"], "", command_names)
    both = suggest(["targets", "log"], "", command_names)
    assert {"quran-pages", "morning-walk"} <= set(both)


def test_targets_no_last_flags_after_name(command_names, db_path):
    add_target("nazr", "quran-pages")
    matched = suggest(["nazr", "log", "quran-pages"], "", command_names)
    assert "-n" in matched and "--no-last" in matched


def test_cal_months_and_years(command_names):
    matched = suggest(["cal"], "", command_names)
    assert {"1", "6", "12", "Mehr", "Shahrivar"} <= set(matched)
    year = str(jdatetime.date.today().year)
    assert year in suggest(["cal", "6"], "", command_names)


def test_day_offsets(command_names):
    matched = suggest(["day"], "", command_names)
    assert {"-1", "-7"} <= set(matched)


def test_prayer_flags(command_names):
    matched = suggest(["p"], "", command_names)
    assert {"j", "s", "q"} <= set(matched)
    # Already-used flags are not repeated.
    assert "j" not in suggest(["p", "j", "mosque"], "", command_names)
    assert "s" in suggest(["p", "j", "mosque"], "", command_names)
    # Alias shares the spec.
    assert "j" in suggest(["pray"], "", command_names)


def test_sleep_time_keywords(command_names):
    for command in ("s", "sleep", "nap"):
        matched = suggest([command], "", command_names)
        assert {"n", "l", "ln"} <= set(matched)


# ── Dynamic catalog completion ─────────────────────────────────────────


def test_sge_completes_categories_multi(command_names, db_path):
    _seed_categories("work/code", "work/email", "rest/nap")
    matched = suggest(["sge"], "", command_names)
    assert {"work/code", "work/email", "rest/nap"} <= set(matched)
    # Substring matching finds path segments.
    assert suggest(["sge"], "code", command_names) == ["work/code"]
    # Already-typed categories are dropped.
    assert "work/code" not in suggest(["sge", "work/code"], "", command_names)
    assert "work/email" in suggest(["sge", "work/code"], "", command_names)


def test_st_completes_categories_and_update_flags(command_names, db_path):
    _seed_categories("work/code", "transport/metro")
    assert "work/code" in suggest(["st4"], "", command_names)
    assert "transport/metro" in suggest(["st4"], "met", command_names)
    flags = suggest(["st4"], "-", command_names)
    assert "-u" in flags and "--update-last" in flags


def test_view_completes_category_filter(command_names, db_path):
    _seed_categories("work/code", "rest/nap")
    assert suggest(["view"], "cod", command_names) == ["work/code"]
    # The filter is a single string: no completion past the first word.
    assert suggest(["view", "work"], "", command_names) == ["-h", "--help"]


def test_search_completes_vocabulary_per_term(command_names, db_path):
    _seed_categories("work/code", "transport/metro")
    matched = suggest(["search"], "", command_names)
    assert {"work", "code", "transport", "metro"} <= set(matched)
    # Later terms still complete; typed terms are skipped.
    matched = suggest(["search", "work"], "", command_names)
    assert "work" not in matched
    assert "code" in matched


def test_free_text_commands_offer_only_help_flags(command_names):
    for command in ("ee", "ege", "et1", "ln", "ln4", "v", "void", "t"):
        assert suggest([command], "", command_names) == ["-h", "--help"]


def test_no_arg_commands_offer_only_help_flags(command_names):
    for command in ("se", "ce", "cge", "u", "recent", "stats", "city", "q"):
        assert suggest([command], "", command_names) == ["-h", "--help"]


def test_dynamic_providers_survive_missing_tables(command_names, tmp_path, monkeypatch):
    # Point at a fresh database without the app schema: no crash, no candidates.
    empty = tmp_path / "empty.db"
    empty.touch()
    monkeypatch.setenv("DAILYDRIVER_DB", str(empty))
    clear_completion_cache()
    matched = suggest(["sge"], "", command_names)
    assert matched == ["-h", "--help"]


# ── prompt_toolkit integration ─────────────────────────────────────────


def test_repl_completer_yields_positioned_completions(command_names):
    completer = ReplCompleter(command_names)
    completions = list(completer.get_completions(Document("tr"), None))
    texts = [c.text for c in completions]
    assert "travel" in texts
    travel = next(c for c in completions if c.text == "travel")
    assert travel.start_position == -len("tr")


def test_repl_completer_completes_subcommands(command_names):
    completer = ReplCompleter(command_names)
    texts = [c.text for c in completer.get_completions(Document("travel o"), None)]
    assert texts == ["on", "off"]


def test_suggest_for_text_matches_split_suggest(command_names):
    assert suggest_for_text("qada ", command_names) == suggest(["qada"], "", command_names)
    assert suggest_for_text("tr", command_names) == suggest([], "tr", command_names)
