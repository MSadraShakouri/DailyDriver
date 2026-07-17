"""Void feature – scratchpad for unfiltered thoughts, separate from the main journal."""

from . import _logic, _migrations

NAME = "void"
VERSION = "1.0.0"


def migrations():
    return _migrations.migrations()


def register_commands(dispatch):
    dispatch["v"] = _logic.log_void
    dispatch["void"] = _logic.log_void
    dispatch["vexport"] = _logic.export_void
