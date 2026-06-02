# dailydriver/features/intentions/__init__.py
"""Intentions feature – to‑dos with deadlines."""

from . import _logic

NAME = "intentions"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["t"] = _logic.add_intention
