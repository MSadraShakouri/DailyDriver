#!/usr/bin/env python3
import sys
from dailydriver.core.schema import init_db
from dailydriver.core.database import cleanup_pending_keywords
from dailydriver.cli.commander import run_single_command, repl

if __name__ == "__main__":
    init_db()
    cleanup_pending_keywords()
    if len(sys.argv) > 1:
        run_single_command(' '.join(sys.argv[1:]))
    else:
        repl()
