# tests/cli/test_shell_complete.py
"""Tests for the ``main.py --complete`` shell completion hook."""

import os
import subprocess
import sys

from dailydriver.cli.commander import command_names_for_completion
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.core.database import PROJECT_ROOT
from dailydriver.features.targets.entries import add_entry as add_target

MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
COMPLETIONS_DIR = os.path.join(PROJECT_ROOT, "completions")


def _complete(line, db_path):
    env = dict(os.environ, DAILYDRIVER_DB=str(db_path))
    result = subprocess.run(
        [sys.executable, MAIN_PY, "--complete", line],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return result.stdout.split()


def test_command_names_cover_dispatch_and_numbered_slots():
    names = command_names_for_completion()
    assert set(make_dispatch()) <= set(names)
    assert {"st1", "et1", "ln1"} <= set(names)


def test_complete_subcommands(db_path):
    assert set(_complete("travel ", db_path)) >= {"on", "off", "status"}
    assert set(_complete("qada ", db_path)) >= {"log", "fasting"}


def test_complete_first_token(db_path):
    assert "travel" in _complete("tr", db_path)
    assert "qada" in _complete("", db_path)


def test_complete_dynamic_target_names(db_path):
    add_target("nazr", "quran-pages")
    assert "quran-pages" in _complete("nazr log ", db_path)
    assert "quran-pages" not in _complete("habit log ", db_path)


def test_complete_unknown_command_is_empty(db_path):
    assert _complete("breakfast with ", db_path) == []


def test_completion_scripts_exist_and_call_the_hook():
    for filename, registration in (
        ("daily.bash", "complete -F _dailydriver_complete"),
        ("daily.zsh", "compdef _dailydriver_complete"),
        ("daily.fish", "complete -c da"),
    ):
        path = os.path.join(COMPLETIONS_DIR, filename)
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        assert "--complete" in content, filename
        assert registration in content, filename


def test_bash_completion_function_returns_candidates(db_path):
    """Source daily.bash and drive the completion function like bash would."""
    bash = os.path.join(COMPLETIONS_DIR, "daily.bash")
    script = (
        f"source {bash}\n"
        'COMP_WORDS=(da travel "")\n'
        "COMP_CWORD=2\n"
        "_dailydriver_complete\n"
        'printf "%s\\n" "${COMPREPLY[@]}"\n'
    )
    env = dict(os.environ, DAILYDRIVER_DB=str(db_path), DAILYDRIVER_MAIN=MAIN_PY)
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert {"on", "off", "status"} <= set(result.stdout.split())
