from datetime import datetime

from dailydriver.core.location import state as city_state
from dailydriver.core.location.rules import add_rule
from dailydriver.core.location.resolver import resolve_city

# 2026-09-26 is a Saturday, 2026-09-27 the Sunday after it.
SATURDAY_10AM = datetime(2026, 9, 26, 10, 0)
SUNDAY_10AM = datetime(2026, 9, 27, 10, 0)


def _sat_rule(conn):
    return add_rule(conn, "Karaj", "0", 8 * 60, 18 * 60)


def test_default_city_without_rules_or_override(db_connection):
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert info.name == "Tehran"
    assert info.reason == "default"
    assert info.until is None
    assert info.weather_url
    assert info.tz == 3.5


def test_schedule_rule_wins_over_default(db_connection):
    _sat_rule(db_connection)
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert (info.name, info.reason) == ("Karaj", "schedule")
    assert info.until == datetime(2026, 9, 26, 18, 0)
    assert info.lat == 35.8327


def test_rule_gap_falls_through_to_default(db_connection):
    _sat_rule(db_connection)
    info = resolve_city(db_connection, SUNDAY_10AM)
    assert (info.name, info.reason) == ("Tehran", "default")


def test_adjacent_rules_hand_over_at_the_shared_boundary(db_connection):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    add_rule(db_connection, "Qom", "0", 12 * 60, 20 * 60)
    assert resolve_city(db_connection, datetime(2026, 9, 26, 11, 59)).name == "Karaj"
    handed = resolve_city(db_connection, datetime(2026, 9, 26, 12, 0))
    assert (handed.name, handed.reason) == ("Qom", "schedule")


def test_override_beats_schedule(db_connection):
    _sat_rule(db_connection)
    city_state.set_override(db_connection, "Qom", None, "indefinite")
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert (info.name, info.reason) == ("Qom", "override")
    assert info.until is None


def test_override_to_default_city_suspends_the_schedule(db_connection):
    _sat_rule(db_connection)
    city_state.set_override(db_connection, None, None, "indefinite")
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert (info.name, info.reason) == ("Tehran", "override")


def test_specific_override_expires_at_its_timestamp(db_connection):
    _sat_rule(db_connection)
    until = int(datetime(2026, 9, 26, 12, 0).timestamp())
    city_state.set_override(db_connection, "Qom", until, "specific")
    before = resolve_city(db_connection, datetime(2026, 9, 26, 11, 59))
    assert (before.name, before.reason, before.until) == ("Qom", "override", datetime(2026, 9, 26, 12, 0))

    # After expiry: a rule exists at that moment, so the schedule governs.
    after = resolve_city(db_connection, datetime(2026, 9, 26, 12, 0))
    assert (after.name, after.reason) == ("Karaj", "schedule")
    # The resolver is pure: the expired row is left for the manager to clear.
    assert city_state.get_state(db_connection)["override_city"] == "Qom"


def test_expired_override_without_rules_falls_to_default(db_connection):
    until = int(datetime(2026, 9, 26, 12, 0).timestamp())
    city_state.set_override(db_connection, "Qom", until, "specific")
    info = resolve_city(db_connection, datetime(2026, 9, 26, 12, 1))
    assert (info.name, info.reason) == ("Tehran", "default")


def test_next_change_override_clears_at_the_stored_transition(db_connection):
    _sat_rule(db_connection)
    until = int(datetime(2026, 9, 26, 8, 0).timestamp())
    city_state.set_override(db_connection, "Qom", until, "next_change")
    assert resolve_city(db_connection, datetime(2026, 9, 26, 7, 59)).name == "Qom"
    assert resolve_city(db_connection, datetime(2026, 9, 26, 8, 0)).name == "Karaj"


def test_next_change_override_without_rules_behaves_like_indefinite(db_connection):
    city_state.set_override(db_connection, "Qom", None, "next_change")
    info = resolve_city(db_connection, SUNDAY_10AM)
    assert (info.name, info.reason) == ("Qom", "override")


def test_travel_mode_wins_over_everything(db_connection):
    _sat_rule(db_connection)
    city_state.set_override(db_connection, "Qom", None, "indefinite")
    db_connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('travel_mode', '1')")
    db_connection.commit()
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert (info.name, info.reason) == ("Tehran", "travel")


def test_custom_default_city_is_used_without_rules(db_connection):
    city_state.set_default_city(db_connection, "Qom")
    assert resolve_city(db_connection, SUNDAY_10AM).name == "Qom"


def test_unknown_default_city_in_state_falls_back_to_tehran(db_connection):
    db_connection.execute("UPDATE city_state SET default_city = 'Atlantis'")
    db_connection.commit()
    info = resolve_city(db_connection, SUNDAY_10AM)
    assert (info.name, info.reason) == ("Tehran", "default")


def test_override_to_unknown_city_falls_through_to_schedule(db_connection):
    _sat_rule(db_connection)
    db_connection.execute(
        "UPDATE city_state SET override_city = 'Atlantis', override_until = NULL, override_mode = 'indefinite'"
    )
    db_connection.commit()
    info = resolve_city(db_connection, SATURDAY_10AM)
    assert (info.name, info.reason) == ("Karaj", "schedule")
