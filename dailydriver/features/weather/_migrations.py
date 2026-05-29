# dailydriver/features/weather/_migrations.py
"""Weather feature migrations."""

def _migration_1(conn):
    """Create weather_log table."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS weather_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL DEFAULT 'Tehran',
            temp_c INTEGER NOT NULL,
            condition_fa TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')
    conn.commit()

def migrations():
    return [_migration_1]
