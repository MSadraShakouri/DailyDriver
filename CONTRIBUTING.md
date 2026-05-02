# Contributing

Thanks for your interest in DailyDriver!

---

## Package Layout

```
dailydriver/
├── core/           # data, parsing, logging (no UI)
├── domains/        # one domain per file (prayer, sleep, hygiene, etc.)
├── display/        # header building, stats, today view
├── cli/            # REPL logic, command implementations
├── ui/             # terminal abstraction (current_ui)
└── utils/          # shared helpers, calendar events
```

- **core/** modules never import from `domains/` or `cli/`.
- **domains/** may import from `core/` and `utils/`.
- **cli/** may import from `domains/` and `display/`.
- **display/** may import from `core/`, `utils/`, and `domains/`.

---

## Adding a New Domain

1. Create a new file in `dailydriver/domains/` (e.g. `exercise.py`).
2. Write the core logic (using `get_connection_cm()` for DB access).
3. Add a command handler in `dailydriver/cli/commander.py` and register it in `make_dispatch()`.
4. Add a help entry in `dailydriver/cli/help.py`.

---

## Adding a New Command

1. Create a file in `dailydriver/cli/` if the logic is substantial, or write the handler directly in `commander.py` for small commands.
2. Register the command in `make_dispatch()`.
3. If it uses the raw line string (e.g. `export 7d`), add it to the tuple in `repl()` and `run_single_command()` so the line is passed directly.

---

## Style

- Follow the existing module docstrings and function naming.
- Keep functions short and focused.
- Use `current_ui.print_line()` and `current_ui.prompt()` for all I/O.

---

## Pull Requests

1. Fork the repo and create a branch.
2. Make your changes and test thoroughly.
3. Open a pull request with a clear description.

For major changes, please open an issue first to discuss your ideas.
