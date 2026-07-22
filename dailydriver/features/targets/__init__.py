"""Targets feature – tracking nazr (finite) and habit (indefinite)."""

from . import _logic, _migrations

NAME = "targets"
VERSION = "1.0.0"


def migrations():
    return _migrations.migrations()


# Command registration will be added in Step 2
# Header will be added in Step 5
