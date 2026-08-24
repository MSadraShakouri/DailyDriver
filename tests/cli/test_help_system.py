"""Tests for the -h/--help system and the registry-driven summary."""

from __future__ import annotations

import pytest

from dailydriver.cli import commander
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.cli.help_registry import HELP, build_summary, command_help, resolve


class TestHelpFlagDetection:
    @pytest.mark.parametrize("parts", [["p", "-h"], ["p", "--help"], ["export", "7d", "-h"]])
    def test_flags_detected(self, parts):
        assert commander._wants_help(parts) is True

    @pytest.mark.parametrize("parts", [["p", "-15"], ["s", "23-7:15"], ["export", "7d", "--txt"], ["p"]])
    def test_non_help_tokens_ignored(self, parts):
        assert commander._wants_help(parts) is False


class TestCommandHelp:
    def test_includes_summary_and_usage(self):
        lines = command_help("p")
        assert any("Log a prayer" in line for line in lines)
        assert any("Usage:" == line for line in lines)

    def test_alias_resolves_to_canonical(self):
        assert resolve("pray")[0] == "p"
        # Alias help shows the canonical command and lists the alias.
        lines = command_help("pray")
        assert lines[0].startswith("p —")
        assert any("aliases: pray" in line for line in lines)

    def test_unknown_command(self):
        assert command_help("zzz") == ["No help available for 'zzz'."]


class TestSummary:
    def test_summary_lists_only_available_commands(self):
        lines = build_summary(["p", "q"])
        text = "\n".join(lines)
        assert " p " in text or "p " in text
        assert "search" not in text  # not in the provided set

    def test_aliases_grouped_with_canonical(self):
        lines = build_summary(["p", "pray"])
        text = "\n".join(lines)
        assert "p (pray)" in text


class TestDispatchHelpInterception:
    def test_help_flag_shows_command_help_not_handler(self, monkeypatch):
        called = {}
        shown = []
        monkeypatch.setattr(commander, "show_command_help", lambda name: shown.append(name))
        dispatch = {"p": lambda line: called.setdefault("p", line)}
        commander._dispatch_line("p -h", dispatch)
        assert shown == ["p"]
        assert "p" not in called  # handler must not run

    def test_offset_arg_runs_handler(self, monkeypatch):
        called = {}
        monkeypatch.setattr(commander, "_show_result", lambda r: None)
        dispatch = {"p": lambda line: called.setdefault("p", line)}
        commander._dispatch_line("p -15", dispatch)
        assert called["p"] == "p -15"


class TestRegistryCoverage:
    def test_every_dispatch_command_has_help(self, db_path):
        dispatch = make_dispatch()
        missing = [name for name in dispatch if name not in HELP]
        assert missing == [], f"commands without help entries: {missing}"

    def test_no_orphan_help_entries(self, db_path):
        dispatch = make_dispatch()
        orphans = [name for name in HELP if name not in dispatch]
        assert orphans == [], f"help entries for unregistered commands: {orphans}"
