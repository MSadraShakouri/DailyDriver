#!/usr/bin/env python3
"""Run the full test suite.  Delegates to pytest for correct discovery."""

import sys

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(["-q", "tests/"]))
