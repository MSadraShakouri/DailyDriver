from dailydriver.features.hygiene.editor import add_hygiene_item, delete_hygiene_item, edit_hygiene_item


def _item(connection, name):
    row = connection.execute("SELECT * FROM hygiene_config WHERE item=?", (name,)).fetchone()
    return dict(row) if row else None


def test_add_item_persists_configuration(db_connection, ui):
    ui.queue("shower", "3", "", "n", "")
    add_hygiene_item(db_connection)
    item = _item(db_connection, "shower")
    assert item["desired_interval_days"] == 3
    assert item["early_warning_enabled"] == 1
    assert item["show_due_today"] == 0


def test_add_item_rejects_duplicate_and_invalid_interval(db_connection, ui):
    db_connection.execute("INSERT INTO hygiene_config (item, desired_interval_days) VALUES ('shower', 3)")
    db_connection.commit()
    ui.queue("shower", "")
    add_hygiene_item(db_connection)
    assert any("already exists" in line for line in ui.lines)

    ui.lines.clear()
    ui.queue("brush", "zero", "")
    add_hygiene_item(db_connection)
    assert any("Invalid interval" in line for line in ui.lines)


def test_edit_item_changes_name_interval_and_flags(db_connection, ui):
    db_connection.execute("""INSERT INTO hygiene_config
           (item, desired_interval_days, early_warning_enabled, show_due_today)
           VALUES ('shower', 3, 1, 1)""")
    db_connection.commit()
    ui.queue("shower", "bath", "5", "n", "n", "")
    edit_hygiene_item(db_connection)
    item = _item(db_connection, "bath")
    assert item["desired_interval_days"] == 5
    assert item["early_warning_enabled"] == 0
    assert item["show_due_today"] == 0


def test_delete_item_requires_confirmation(db_connection, ui):
    db_connection.execute("INSERT INTO hygiene_config (item, desired_interval_days) VALUES ('shower', 3)")
    db_connection.commit()
    ui.queue("shower", "n", "")
    delete_hygiene_item(db_connection)
    assert _item(db_connection, "shower") is not None

    ui.queue("shower", "y", "")
    delete_hygiene_item(db_connection)
    assert _item(db_connection, "shower") is None
