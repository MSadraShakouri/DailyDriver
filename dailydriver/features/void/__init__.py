"""Unfiltered scratchpad feature adapter."""

from .commands import log_void
from .export import export_void
from .migrations import migrations

NAME = "void"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["v"] = log_void
    dispatch["void"] = log_void
    dispatch["vexport"] = export_void
