"""Intentions feature adapter."""

from .commands import add_intention

NAME = "intentions"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["t"] = add_intention
