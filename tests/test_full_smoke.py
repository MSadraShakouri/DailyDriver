# tests/test_full_smoke.py
"""Comprehensive smoke test – exercises every command path without real DB."""

import atexit
import inspect
import os
import sqlite3
import subprocess
import sys
import tempfile

# Use a temporary file so that multiple connections share the same database
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
atexit.register(lambda: os.unlink(_tmp_db.name))
os.environ["DAILYDRIVER_DB"] = _tmp_db.name

sys.path.insert(0, ".")

from dailydriver.cli.dispatcher import make_dispatch  # noqa: E402
from dailydriver.core import entry_writer  # noqa: E402
from dailydriver.core.migration import run_migrations  # noqa: E402
from dailydriver.ui.terminal_ui import current_ui  # noqa: E402

# ========== SETUP ==========
run_migrations()

# Patch UI to never pause for input
current_ui.confirm_time = lambda *a, **kw: True
current_ui.confirm = lambda *a, **kw: True
current_ui.prompt = lambda *a, **kw: ""
current_ui.print_line = lambda *a, **kw: None
current_ui.clear = lambda: None

# Suppress keyword learning (avoids needing populated keyword DB)
_original_save = entry_writer._save_entry


def _save_no_keywords(conn, cmd, started_at, duration, selected_paths):
    import dailydriver.core.keyword_learner as kl

    real = kl.learn_keywords
    kl.learn_keywords = lambda *a, **kw: None
    result = _original_save(conn, cmd, started_at, duration, selected_paths)
    kl.learn_keywords = real
    return result


entry_writer._save_entry = _save_no_keywords

# ========== DISPATCH SMOKE ==========
dispatch = make_dispatch()

# Overwrite interactive viewers that would loop forever
dispatch["view"] = lambda _: None
dispatch["search"] = lambda _: None
dispatch["day"] = lambda _: None
dispatch["birthdays"] = lambda _: None

errors = []
print("=== Dispatch smoke test (every handler accepts 'test') ===")
for key, fn in dispatch.items():
    if key == "q":
        continue
    try:
        inspect.signature(fn).bind("test")
    except TypeError as e:
        errors.append(f"  {key}: {e}")
if errors:
    print("FAILED:")
    for e in errors:
        print(e)
    sys.exit(1)
print("  All handlers OK\n")

# ========== COMMAND EXECUTION SMOKE ==========
print("=== Command execution smoke test (no real DB touches) ===")


def run_cmd(cmd_line):
    parts = cmd_line.strip().split()
    first = parts[0].lower()
    handler = dispatch.get(first)
    if handler is None:
        return None
    try:
        return handler(cmd_line)
    except Exception as e:
        return f"CRASH: {e}"


crashes = []


def run_batch(label, cmds):
    for name, cmd in cmds:
        result = run_cmd(cmd)
        if isinstance(result, str) and result.startswith("CRASH"):
            crashes.append(f"{name}: {result}")


# Prayer
run_batch(
    "prayer",
    [
        ("prayer: p", "p"),
        ("prayer: p -15", "p -15"),
        ("prayer: p 05:30", "p 05:30"),
        ("prayer: p q", "p q"),
        ("prayer: qada", "qada"),
    ],
)

# Sleep / Nap
run_batch(
    "sleep/nap",
    [
        ("sleep: s 23:00 07:15", "s 23:00 07:15"),
        ("sleep: sleep", "sleep"),
    ],
)
# Clean up sleep logs to avoid UNIQUE constraint
sqlite3.connect(_tmp_db.name).execute("DELETE FROM sleep_logs").execute("DELETE FROM nap_logs").connection.commit()

run_batch(
    "nap",
    [
        ("nap: nap 14:00 14:25", "nap 14:00 14:25"),
        ("nap: nap 14-14:25", "nap 14-14:25"),
    ],
)

# Events
run_batch(
    "events",
    [
        ("events: se", "se"),
        ("events: ce", "ce"),
        ("events: ee test", "ee test"),
        ("events: ln test", "ln test"),
        ("events: sge work", "sge work"),
        ("events: ege done", "ege done"),
        ("events: cge", "cge"),
    ],
)

# Calendar
run_batch(
    "calendar",
    [
        ("calendar: cal", "cal"),
        ("calendar: year", "year"),
        ("calendar: hijri", "hijri"),
    ],
)

# Birthdays
run_batch(
    "birthdays",
    [
        ("birthdays: bd", "bd"),
        ("birthdays: birthdays", "birthdays"),
    ],
)

# Intentions
run_batch(
    "intentions",
    [
        ("intentions: t", "t"),
    ],
)

# Viewing / Search / Stats / Help
run_batch(
    "view/search/stats/help",
    [
        ("view: view", "view"),
        ("view: recent", "recent"),
        ("search: search test", "search test"),
        ("stats: stats", "stats"),
        ("help: ?", "?"),
        ("help: h", "h"),
    ],
)

# Journal (free text)
run_batch(
    "journal",
    [
        ("journal: coffee", "coffee"),
        ("journal: l5m test", "l5m test"),
        ("journal: ln chained", "ln chained"),
    ],
)

if crashes:
    print("FAILED:")
    for c in crashes:
        print(f"  {c}")
    sys.exit(1)
print("  All commands executed without crash\n")

# ========== ALIASES SMOKE ==========
print("=== Alias smoke test ===")
aliases = {"pray": "p", "sleep": "s", "h": "?", "qada": "p q"}
for alias, target in aliases.items():
    if alias not in dispatch:
        crashes.append(f"alias missing: {alias} (should map to {target})")
if crashes:
    print("FAILED:")
    for c in crashes:
        print(f"  {c}")
    sys.exit(1)
print("  All aliases present\n")

print("✅ Full smoke test passed")


# Make the smoke test runnable by pytest
def test_full_smoke_as_subprocess():
    """Run the smoke test script and assert it passes."""

    r = subprocess.run(
        [sys.executable, __file__],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"Smoke test failed:\n{r.stdout}\n{r.stderr}"
