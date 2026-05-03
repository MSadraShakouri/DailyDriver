#!/usr/bin/env python3
import sys
from dailydriver.core.migration import run_migrations
from dailydriver.cli.commander import run_single_command, repl

if __name__ == "__main__":
    run_migrations()
    if len(sys.argv) > 1:
        run_single_command(' '.join(sys.argv[1:]))
    else:
        repl()
