#!/usr/bin/env python3
"""Discover and run all tests in the tests/ directory."""
import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a temporary database
tmp_dir = tempfile.mkdtemp()
db_path = os.path.join(tmp_dir, "test.db")
os.environ["DAILYDRIVER_DB"] = db_path

from dailydriver.core.migration import run_migrations
run_migrations()

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    # Clean up
    shutil.rmtree(tmp_dir, ignore_errors=True)
    sys.exit(0 if result.wasSuccessful() else 1)
