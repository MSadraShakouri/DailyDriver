"""Void feature migrations."""


def _migration_1(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS void_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            description TEXT
        )
    """)
    conn.commit()


def migrations():
    return [_migration_1]
