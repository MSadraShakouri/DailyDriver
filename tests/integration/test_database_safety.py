"""Upgrade invariants exercised against a current, file-backed database."""

import hashlib
import json

from dailydriver.core.database import get_connection
from dailydriver.core.migration import run_migrations


def _logical_fingerprint(connection):
    digest = hashlib.sha256()
    objects = connection.execute("""SELECT type, name, COALESCE(sql, '') AS sql
           FROM sqlite_master
           WHERE name NOT LIKE 'sqlite_%'
           ORDER BY type, name""").fetchall()
    for object_type, name, sql in objects:
        digest.update(json.dumps([object_type, name, sql]).encode())
        if object_type != "table" or name.endswith("_fts"):
            continue
        quoted = name.replace('"', '""')
        rows = connection.execute(f'SELECT * FROM "{quoted}"').fetchall()
        serialized = sorted(repr(tuple(row)) for row in rows)
        digest.update(json.dumps(serialized).encode())
    return digest.hexdigest()


def test_current_migrations_are_idempotent_and_data_preserving(db_path):
    connection = get_connection(auto=False)
    try:
        before = _logical_fingerprint(connection)
    finally:
        connection.close()

    run_migrations()

    connection = get_connection(auto=False)
    try:
        assert _logical_fingerprint(connection) == before
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
