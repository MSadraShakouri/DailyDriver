# Test suite

The test tree mirrors `dailydriver/` so ownership is visible:

```text
tests/
├── cli/
├── core/
├── display/
├── features/
│   ├── birthdays/
│   ├── calendar/
│   ├── events/
│   ├── hygiene/
│   ├── intentions/
│   ├── prayer/
│   ├── qada/
│   ├── sleep/
│   ├── targets/
│   ├── void/
│   └── weather/
├── integration/
├── ui/
└── utils/
```

## Test boundaries

- Pure calculations use direct inputs and avoid a database fixture.
- Persistence tests request `db_path` or `db_connection`. Each gets a copy of
  one fully migrated template database through `DAILYDRIVER_DB`.
- Interactive tests request `ui`, a deterministic recorder for prompts and
  output. They test parsing/delegation rather than reproducing implementation
  logic in the test.
- Integration tests exercise package contracts across real migrated schemas.
- Network and filesystem boundaries use temporary paths or explicit fakes.
- Tests must not mutate repository data files or replace global UI/database
  state at import time.

Run the suite:

```bash
python -m pytest
```

Run source and branch coverage (the configured floor is enforced):

```bash
coverage run -m pytest
coverage report
```

Coverage is a regression signal, not proof of correctness. Database migration
idempotence, SQLite integrity, cross-feature header composition, and command
registration have explicit integration tests because those contracts are more
important than raw line coverage.
