# Feature Hook Specification

Each feature lives in a sub‑package of `dailydriver/features/`.  
It may expose any of the following optional hooks using plain functions
(duck‑typed – no base class required).

---

## `NAME: str`
Human‑readable feature name (e.g., `"weather"`).

## `VERSION: str`
Semantic version string (e.g., `"1.0.0"`). Bump when the feature's public
interface changes.

---

## `migrations() -> list[callable]`
Return an ordered list of migration functions for this feature.
Each function receives a single `sqlite3.Connection` argument.

Example:
```python
def _migration_1(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS ...")

def migrations():
    return [_migration_1]
```

## `register_commands(dispatch: dict) -> None`
Add entries to the dispatcher dictionary. Keys are command names,
values are callables that accept the raw command line string.

Example:
```python
def register_commands(dispatch):
    dispatch["p"] = log_prayer
    dispatch["pray"] = log_prayer
```

## `header_sections() -> list[tuple[int, str]] | list[str]`
Return header content.
- If a list of plain strings, each string is printed as a separate header line.
- If a list of `(priority, text)` tuples, lower priority numbers appear higher
  on screen. The core sorts by priority ascending, then prints the text lines.

Example:
```python
def header_sections():
    return [(20, "☀️ 24°C clear")]
```

## `stats_sections() -> dict | None`
Return key‑value pairs that will be included in the `stats` command output.
Keys are section titles, values are the text to display.

Example:
```python
def stats_sections():
    return {"Weather": "Last fetch: 12:34"}
```

## `register_aliases(dispatch: dict) -> None`
Add short aliases for commands. Works exactly like `register_commands` but
intended for secondary names (e.g., `pray` → `p`).

Example:
```python
def register_aliases(dispatch):
    dispatch["pray"] = dispatch["p"]
```

---

## Feature loading order

Features are loaded in the order they appear in the `ENABLED` list
(in `dailydriver/features/__init__.py`). This order controls:
- The order in which header sections appear (when no explicit priority is given).
- The order in which commands are registered (later features can override
  earlier ones if they register the same command name – use with caution).