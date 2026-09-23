import re
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

from dailydriver.cli.commands.city import city_command
from dailydriver.core.location import state as city_state
from dailydriver.core.location.rules import add_rule, list_rules

# Sorted registry menu: [1] Karaj  [2] Mashhad  [3] Qom  [4] Tehran


@contextmanager
def manager_view():
    """Patch the app header + width the way the house managers render."""
    with (
        patch("dailydriver.cli.commands.city.build_header_data", return_value={}),
        patch("dailydriver.cli.commands.city.print_header"),
        patch("dailydriver.cli.commands.city.get_width", lambda: 80),
    ):
        yield


def test_main_screen_shows_current_city_and_reason(db_connection, ui):
    ui.queue("q")
    with manager_view():
        city_command("city")
    assert any("Current city: Tehran (default)" in line for line in ui.lines)
    assert any("No schedule rules" in line for line in ui.lines)


def test_help_screen(db_connection, ui):
    ui.queue("?", "", "q")
    with manager_view():
        city_command("city")
    assert any("City Manager Help" in line for line in ui.lines)
    assert any("c   Change city now" in line for line in ui.lines)


def test_narrow_terminal_stacks_commands_and_transitions(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("q")
    with (
        patch("dailydriver.cli.commands.city.build_header_data", return_value={}),
        patch("dailydriver.cli.commands.city.print_header"),
        patch("dailydriver.cli.commands.city.get_width", lambda: 50),
    ):
        city_command("city")
    assert "  (c)hange now" in ui.lines  # one command per line, no spread
    assert any(line.startswith("  Sat ") and "-> Karaj" in line for line in ui.lines)


def test_narrow_terminal_help_drops_the_box(db_connection, ui):
    ui.queue("?", "", "q")
    with (
        patch("dailydriver.cli.commands.city.build_header_data", return_value={}),
        patch("dailydriver.cli.commands.city.print_header"),
        patch("dailydriver.cli.commands.city.get_width", lambda: 50),
    ):
        city_command("city")
    assert any("City Manager Help" in line for line in ui.lines)
    assert not any("┌" in line for line in ui.lines)


def test_rules_table_numbers_rows_in_list_order(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    add_rule(db_connection, "Qom", "3", 13 * 60, 14 * 60)
    ui.queue("q")
    with manager_view():
        city_command("city")
    rows = [line for line in ui.lines if line.lstrip().startswith(("1 ", "2 ")) and ("Karaj" in line or "Qom" in line)]
    assert len(rows) == 2
    assert rows[0].lstrip().startswith("1 ") and "Karaj" in rows[0]
    assert rows[1].lstrip().startswith("2 ") and "Qom" in rows[1]


def test_unknown_command_is_reported(db_connection, ui):
    ui.queue("x", "", "q")
    with manager_view():
        city_command("city")
    assert any("Unknown command. Type ? for help." in line for line in ui.lines)


def test_change_city_to_indefinite_override(db_connection, ui):
    ui.queue("c", "1", "3", "", "q")  # change -> Karaj -> indefinite -> quit
    with manager_view():
        city_command("city")
    state = city_state.get_state(db_connection)
    assert (state["override_city"], state["override_mode"], state["override_until"]) == ("Karaj", "indefinite", None)
    assert any("Override set: Karaj (indefinite)." in line for line in ui.lines)


def test_change_to_default_city_until_specific_datetime(db_connection, ui):
    ui.queue("c", "d", "2", "2026-10-01 08:00", "", "q")
    with manager_view():
        city_command("city")
    state = city_state.get_state(db_connection)
    assert state["override_city"] is None  # NULL city = suspend to default
    assert state["override_mode"] == "specific"
    assert state["override_until"] == int(datetime(2026, 10, 1, 8, 0).timestamp())


def test_next_change_override_without_rules_stores_no_expiry(db_connection, ui):
    ui.queue("c", "1", "1", "", "q")
    with manager_view():
        city_command("city")
    state = city_state.get_state(db_connection)
    assert (state["override_city"], state["override_mode"], state["override_until"]) == ("Karaj", "next_change", None)


def test_invalid_datetime_prompts_again_without_saving(db_connection, ui):
    ui.queue("c", "1", "2", "not a date", "n", "q")
    with manager_view():
        city_command("city")
    assert any("Use YYYY-MM-DD HH:MM" in line for line in ui.lines)
    assert city_state.get_state(db_connection)["override_mode"] is None


def test_edit_default_city(db_connection, ui):
    ui.queue("d", "3", "", "q")  # default -> Qom -> quit
    with manager_view():
        city_command("city")
    assert city_state.get_default_city(db_connection) == "Qom"
    assert any("Default city set to Qom." in line for line in ui.lines)


def test_add_rule_and_preview_transitions(db_connection, ui):
    ui.queue("s", "a", "1", "0", "08:00-12:00", "", "b", "q")  # schedule -> add Karaj Sat 8-12 -> back -> quit
    with manager_view():
        city_command("city")
    rules = list_rules(db_connection)
    assert len(rules) == 1
    assert (rules[0].city, rules[0].days, rules[0].from_min, rules[0].to_min) == ("Karaj", (0,), 480, 720)
    assert any("Rule added: Karaj — Sat 08:00-12:00" in line for line in ui.lines)
    assert any("-> Karaj" in line for line in ui.lines)
    assert any("Current city:" in line for line in ui.lines)


def test_transition_lines_carry_dates(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("q")
    with manager_view():
        city_command("city")
    joined = "\n".join(ui.lines)
    # The next three transitions share one line; each must carry a date so
    # successive weeks are distinguishable.
    matches = re.findall(r"\w{3} \d{2} \w{3} \d{2}:\d{2} -> Karaj", joined)
    assert len(matches) == 3


def test_rules_table_lists_every_rule(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    add_rule(db_connection, "Qom", "3 5", 13 * 60, 14 * 60)
    ui.queue("q")
    with manager_view():
        city_command("city")
    joined = "\n".join(ui.lines)
    assert "Karaj" in joined and "Sat" in joined and "08:00-12:00" in joined
    assert "Tue, Thu" in joined and "13:00-14:00" in joined


def test_add_rule_with_space_separated_days(db_connection, ui):
    ui.queue("s", "a", "1", "0 2 3 4", "07:00-17:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.city, rule.days, rule.from_min, rule.to_min) == ("Karaj", (0, 2, 3, 4), 420, 1020)
    assert any("Rule added: Karaj — Sat, Mon, Tue, Wed 07:00-17:00" in line for line in ui.lines)
    assert any("Sat, Mon, Tue, Wed" in line and "07:00-17:00" in line for line in ui.lines)


def test_invalid_days_retry_keeps_the_chosen_city(db_connection, ui):
    ui.queue("s", "a", "1", "34", "0 2", "07:00-17:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.city, rule.days) == ("Karaj", (0, 2))
    assert any("Invalid day '34'" in line for line in ui.lines)
    assert any("0=Sat  1=Sun  2=Mon" in line for line in ui.lines)
    assert any("-> Sat, Mon" in line for line in ui.lines)


def test_invalid_time_retry_keeps_city_and_days(db_connection, ui):
    ui.queue("s", "a", "1", "0 2", "oops", "08:00-12:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.city, rule.days, rule.from_min, rule.to_min) == ("Karaj", (0, 2), 480, 720)
    assert any("Use HH:MM-HH:MM" in line for line in ui.lines)
    assert any("-> Sat, Mon" in line for line in ui.lines)


def test_time_range_accepts_flexible_separators(db_connection, ui):
    ui.queue("s", "a", "1", "all", "08:00 to 12:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.days, rule.from_min, rule.to_min) == (tuple(range(7)), 480, 720)
    assert any("Rule added: Karaj — every day 08:00-12:00" in line for line in ui.lines)


def test_day_names_and_persian_digits_are_accepted(db_connection, ui):
    ui.queue("s", "a", "1", "۵ ۶", "08:00-12:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.days, rule.from_min, rule.to_min) == ((5, 6), 480, 720)
    assert any("-> Thu, Fri" in line for line in ui.lines)


def test_day_names_accepted_in_english(db_connection, ui):
    ui.queue("s", "a", "1", "mon-fri", "09:00-14:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.days, rule.from_min, rule.to_min) == ((2, 3, 4, 5, 6), 540, 840)
    assert any("Rule added: Karaj — Mon, Tue, Wed, Thu, Fri 09:00-14:00" in line for line in ui.lines)


def test_overlapping_rule_is_rejected_at_save(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("s", "a", "4", "0", "08:00-18:00", "", "b", "q")  # Tehran Sat 8-18 overlaps
    with manager_view():
        city_command("city")
    assert any("Overlaps the existing Karaj rule" in line for line in ui.lines)
    assert len(list_rules(db_connection)) == 1


def test_overlap_retry_keeps_city_and_days(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("s", "a", "1", "0 2", "08:00-18:00", "13:00-15:00", "", "b", "q")
    with manager_view():
        city_command("city")
    rules = list_rules(db_connection)
    # The conflicting window is refused; the retried window lands on the new days.
    assert len(rules) == 2
    assert rules[1].days == (0, 2) and (rules[1].from_min, rules[1].to_min) == (780, 900)
    assert any("Overlaps the existing Karaj rule" in line for line in ui.lines)


def test_edit_rule_inline(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("s", "e 1", "1", "0 2", "08:00-12:00", "", "b", "q")
    with manager_view():
        city_command("city")
    (rule,) = list_rules(db_connection)
    assert (rule.days, rule.from_min, rule.to_min) == ((0, 2), 480, 720)
    assert any("Rule updated: Karaj — Sat, Mon 08:00-12:00" in line for line in ui.lines)


def test_edit_without_number_shows_usage(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("s", "e", "", "", "b", "q")
    with manager_view():
        city_command("city")
    assert any("Usage: e <#>" in line for line in ui.lines)
    (rule,) = list_rules(db_connection)  # untouched
    assert rule.days == (0,)


def test_delete_rule_inline(db_connection, ui):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    ui.queue("s", "d 1", "", "b", "q")
    with manager_view():
        city_command("city")
    assert list_rules(db_connection) == []
    assert any("Rule deleted." in line for line in ui.lines)


def test_view_and_clear_override(db_connection, ui):
    city_state.set_override(db_connection, "Qom", None, "indefinite")
    ui.queue("o", "", "q")  # view/clear (recorder confirms) -> quit
    with manager_view():
        city_command("city")
    state = city_state.get_state(db_connection)
    assert state["override_mode"] is None
    assert any("Override cleared." in line for line in ui.lines)


def test_view_override_when_none_active(db_connection, ui):
    ui.queue("o", "", "q")
    with manager_view():
        city_command("city")
    assert any("No override active." in line for line in ui.lines)
