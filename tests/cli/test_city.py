from datetime import datetime

from dailydriver.cli.commands.city import city_command
from dailydriver.core.location import state as city_state
from dailydriver.core.location.rules import add_rule, list_rules

# Sorted registry menu: [1] Karaj  [2] Mashhad  [3] Qom  [4] Tehran


def test_main_screen_shows_current_city_and_reason(db_connection, ui):
    ui.queue("q")
    city_command("city")
    assert any("Current city: Tehran (default)" in line for line in ui.lines)
    assert any("No schedule rules" in line for line in ui.lines)


def test_change_city_to_indefinite_override(db_connection, ui):
    ui.queue("1", "1", "3", "q")  # change -> Karaj -> indefinite -> quit
    city_command("city")
    state = city_state.get_state(db_connection)
    assert (state["override_city"], state["override_mode"], state["override_until"]) == ("Karaj", "indefinite", None)
    assert any("Override set: Karaj (indefinite)." in line for line in ui.lines)


def test_change_to_default_city_until_specific_datetime(db_connection, ui):
    ui.queue("1", "d", "2", "2026-10-01 08:00", "q")
    city_command("city")
    state = city_state.get_state(db_connection)
    assert state["override_city"] is None  # NULL city = suspend to default
    assert state["override_mode"] == "specific"
    assert state["override_until"] == int(datetime(2026, 10, 1, 8, 0).timestamp())


def test_next_change_override_without_rules_stores_no_expiry(db_connection, ui):
    ui.queue("1", "1", "1", "q")
    city_command("city")
    state = city_state.get_state(db_connection)
    assert (state["override_city"], state["override_mode"], state["override_until"]) == ("Karaj", "next_change", None)


def test_invalid_datetime_prompts_again_without_saving(db_connection, ui):
    ui.queue("1", "1", "2", "not a date", "n", "q")
    city_command("city")
    assert any("Invalid date & time." in line for line in ui.lines)
    assert city_state.get_state(db_connection)["override_mode"] is None


def test_edit_default_city(db_connection, ui):
    ui.queue("3", "3", "q")  # edit default -> Qom -> quit
    city_command("city")
    assert city_state.get_default_city(db_connection) == "Qom"
    assert any("Default city set to Qom." in line for line in ui.lines)


def test_add_rule_and_preview_transitions(db_connection, ui):
    ui.queue("2", "a", "1", "0", "08:00-12:00", "q", "q")  # schedule -> add Karaj Sat 8-12 -> back -> quit
    city_command("city")
    rules = list_rules(db_connection)
    assert len(rules) == 1
    assert (rules[0].city, rules[0].days, rules[0].from_min, rules[0].to_min) == ("Karaj", (0,), 480, 720)
    assert any("Rule added (id 1)." in line for line in ui.lines)
    assert any("Upcoming transitions:" in line for line in ui.lines)
    assert any("Current city:" in line for line in ui.lines)


def test_overlapping_rule_is_rejected_at_save(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("2", "a", "4", "0", "08:00-18:00", "q", "q")  # Tehran Sat 8-18 overlaps
    city_command("city")
    assert any("Invalid rule: Overlaps" in line for line in ui.lines)
    assert len(list_rules(db_connection)) == 1


def test_delete_rule(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("2", "d", "1", "q", "q")
    city_command("city")
    assert list_rules(db_connection) == []
    assert any("Rule deleted." in line for line in ui.lines)


def test_view_and_clear_override(db_connection, ui):
    city_state.set_override(db_connection, "Qom", None, "indefinite")
    ui.queue("4", "q")  # view/clear (recorder confirms) -> quit
    city_command("city")
    state = city_state.get_state(db_connection)
    assert state["override_mode"] is None
    assert any("Override cleared." in line for line in ui.lines)


def test_view_override_when_none_active(db_connection, ui):
    ui.queue("4", "q")
    city_command("city")
    assert any("No override active." in line for line in ui.lines)
