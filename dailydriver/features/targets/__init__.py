"""Finite goals and indefinite habits feature adapter."""

from . import header
from .export import export_items
from .migrations import migrations
from .router import dispatch

NAME = "targets"
VERSION = "1.0.0"


def header_sections(conn, today, target_date, is_today):
    return header.header_sections(conn, today, target_date, is_today)


def register_commands(command_map):
    command_map["nazr"] = lambda command: dispatch(command, kind="nazr")
    command_map["habit"] = lambda command: dispatch(command, kind="habit")
    command_map["targets"] = lambda command: dispatch(command, kind=None)
