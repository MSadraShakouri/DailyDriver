from datetime import datetime

import pytest

from dailydriver.core.location.rules import (
    MINUTES_PER_DAY,
    Rule,
    RuleConflict,
    RuleError,
    active_rule,
    add_rule,
    delete_rule,
    format_clock_minutes,
    format_days,
    iranian_weekday,
    list_rules,
    next_rule_start,
    normalize_days,
    parse_clock_minutes,
    rules_overlap,
    update_rule,
)


def _rule(rule_id, city, days, from_min, to_min):
    return Rule(id=rule_id, city=city, days=tuple(days), from_min=from_min, to_min=to_min)


def test_days_normalization():
    assert normalize_days("all") == tuple(range(7))
    assert normalize_days("daily") == tuple(range(7))
    assert normalize_days("0,3,4") == (0, 3, 4)
    assert normalize_days("0, 3 ,3") == (0, 3)
    assert normalize_days(2) == (2,)
    assert normalize_days([6, 0]) == (0, 6)
    for bad in ("", "7", "-1", "0,9", [8], [], "x"):
        with pytest.raises(RuleError):
            normalize_days(bad)


def test_days_space_separated_tokens_are_not_glued():
    # Regression: '0 2' once became int('02') == 2 (Monday only).
    assert normalize_days("0 2") == (0, 2)
    assert normalize_days("0 2 3 4") == (0, 2, 3, 4)
    assert normalize_days("3 4") == (3, 4)
    assert normalize_days("  1   5  ") == (1, 5)


def test_days_names_ranges_and_persian_digits():
    assert normalize_days("monday") == (2,)
    assert normalize_days("sat mon") == (0, 2)
    assert normalize_days("Tue,Wed") == (3, 4)
    assert normalize_days("th") == (5,)
    assert normalize_days("0-4") == (0, 1, 2, 3, 4)
    assert normalize_days("mon-fri") == (2, 3, 4, 5, 6)
    assert normalize_days("۵ ۶") == (5, 6)
    assert normalize_days("sat-thu") == tuple(range(6))
    for bad in ("fri-mon", "s", "mon-tue-wed", "9-10"):
        with pytest.raises(RuleError):
            normalize_days(bad)


def test_format_days():
    assert format_days((0,)) == "Sat"
    assert format_days((2, 0)) == "Sat, Mon"
    assert format_days(tuple(range(7))) == "every day"


def test_clock_parsing_and_formatting():
    assert parse_clock_minutes("8:00") == 480
    assert parse_clock_minutes("18:30") == 1110
    assert parse_clock_minutes("730") == 450
    assert parse_clock_minutes("0:00") == 0
    assert parse_clock_minutes("24:00") == MINUTES_PER_DAY
    assert format_clock_minutes(480) == "08:00"
    for bad in ("", "abc", "7:5x", "25:00", "12:60", "24:30"):
        with pytest.raises(RuleError):
            parse_clock_minutes(bad)


def test_add_list_and_delete_rules(db_connection):
    rule_id = add_rule(db_connection, "Karaj", "0,3", 8 * 60, 12 * 60)
    add_rule(db_connection, "Tehran", "all", 12 * 60, 20 * 60)
    rules = list_rules(db_connection)
    assert [r.city for r in rules] == ["Karaj", "Tehran"]
    assert rules[0].days == (0, 3)
    assert rules[0].covers(0, 8 * 60) and rules[0].covers(0, 11 * 60 + 59)
    assert not rules[0].covers(0, 12 * 60)  # exclusive to

    delete_rule(db_connection, rule_id)
    assert [r.city for r in list_rules(db_connection)] == ["Tehran"]
    with pytest.raises(RuleError):
        delete_rule(db_connection, rule_id)


def test_overlapping_rules_are_rejected_at_save(db_connection):
    add_rule(db_connection, "Karaj", "0,3", 8 * 60, 12 * 60)
    with pytest.raises(RuleConflict):
        add_rule(db_connection, "Tehran", "0", 10 * 60, 14 * 60)
    # Intersecting on any shared day is enough.
    with pytest.raises(RuleConflict):
        add_rule(db_connection, "Tehran", "3,4", 11 * 60, 12 * 60)
    assert len(list_rules(db_connection)) == 1


def test_adjacent_rules_are_accepted(db_connection):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    add_rule(db_connection, "Tehran", "0", 12 * 60, 20 * 60)
    assert len(list_rules(db_connection)) == 2


def test_same_times_on_disjoint_days_are_accepted(db_connection):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    add_rule(db_connection, "Tehran", "1", 8 * 60, 12 * 60)
    assert len(list_rules(db_connection)) == 2


def test_update_rejects_conflict_with_other_rules_and_bad_shapes(db_connection):
    first = add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)
    second = add_rule(db_connection, "Tehran", "0", 12 * 60, 20 * 60)
    with pytest.raises(RuleConflict):
        update_rule(db_connection, second, "Tehran", "0", 11 * 60, 21 * 60)
    update_rule(db_connection, second, "Qom", "1", 9 * 60, 21 * 60)
    rules = {r.id: r for r in list_rules(db_connection)}
    assert rules[second].city == "Qom"
    with pytest.raises(RuleError):
        update_rule(db_connection, first, "Karaj", "0", 13 * 60, 12 * 60)
    with pytest.raises(RuleError):
        update_rule(db_connection, 999, "Karaj", "0", 8 * 60, 9 * 60)


def test_window_validation_rejects_overnight_and_inverted_ranges(db_connection):
    for frm, to in ((13 * 60, 12 * 60), (0, 0), (-5, 60), (0, MINUTES_PER_DAY + 1)):
        with pytest.raises(RuleError):
            add_rule(db_connection, "Karaj", "0", frm, to)


def test_rules_overlap_helper():
    karaj = _rule(1, "Karaj", (0,), 480, 720)
    assert rules_overlap((0,), 600, 700, karaj)
    assert rules_overlap((0, 2), 700, 800, karaj)
    assert not rules_overlap((0,), 720, 800, karaj)  # adjacent
    assert not rules_overlap((1,), 600, 700, karaj)  # different day


def test_iranian_weekday_maps_saturday_to_zero():
    # 2026-09-26 is a Saturday; 2026-09-23 the Wednesday before it.
    assert iranian_weekday(datetime(2026, 9, 26).date()) == 0
    assert iranian_weekday(datetime(2026, 9, 23).date()) == 4
    assert iranian_weekday(datetime(2026, 10, 2).date()) == 6  # Friday


def test_next_rule_start_skips_today_after_its_start(db_connection):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 18 * 60)  # Saturdays
    # Saturday 09:00 -> next start is the following Saturday.
    start, rule = next_rule_start(list_rules(db_connection), datetime(2026, 9, 26, 9, 0))
    assert start == datetime(2026, 10, 3, 8, 0)
    assert rule.city == "Karaj"
    # Saturday 07:59 -> today's 08:00 start is still ahead.
    start, _ = next_rule_start(list_rules(db_connection), datetime(2026, 9, 26, 7, 59))
    assert start == datetime(2026, 9, 26, 8, 0)


def test_next_rule_start_picks_the_soonest_of_several_rules(db_connection):
    add_rule(db_connection, "Karaj", "0", 8 * 60, 12 * 60)  # Sat
    add_rule(db_connection, "Qom", "4", 10 * 60, 14 * 60)  # Wed
    start, rule = next_rule_start(list_rules(db_connection), datetime(2026, 9, 24, 15, 0))  # Thu
    assert (start, rule.city) == (datetime(2026, 9, 26, 8, 0), "Karaj")
    start, rule = next_rule_start(list_rules(db_connection), datetime(2026, 9, 26, 13, 0))  # Sat
    assert (start, rule.city) == (datetime(2026, 9, 30, 10, 0), "Qom")


def test_next_rule_start_without_rules(db_connection):
    assert next_rule_start(list_rules(db_connection), datetime(2026, 9, 24, 15, 0)) is None


def test_active_rule_helper():
    rules = [_rule(1, "Karaj", (0,), 480, 720)]
    assert active_rule(rules, 0, 480).city == "Karaj"
    assert active_rule(rules, 0, 719).city == "Karaj"
    assert active_rule(rules, 0, 720) is None
    assert active_rule(rules, 1, 600) is None
