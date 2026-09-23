from datetime import datetime

import jdatetime

from dailydriver.features.prayer import nudges
from dailydriver.features.prayer.windows import SlotWindow

TARGET_DATE = jdatetime.date(1405, 7, 1)
TODAY_STR = "1405-07-01"
G = nudges.GREEN
Y = nudges.YELLOW
R = nudges.RED
RESET = nudges.RESET


def _window(opens, green_until, red_from, deadline):
    base = datetime(2026, 9, 23)  # Mehr 1, 1405
    at = lambda hm: base.replace(hour=hm[0], minute=hm[1])
    return SlotWindow(opens=at(opens), green_until=at(green_until), red_from=at(red_from), deadline=at(deadline))


def _fixed_windows():
    return {
        "fajr": _window((4, 31), (4, 50), (5, 25), (5, 55)),
        "dhuhr_asr": _window((11, 58), (15, 25), (16, 2), (18, 2)),
        "maghrib_isha": _window((18, 20), (19, 7), (21, 17), (23, 17)),
    }


def _nudges(db_connection, monkeypatch, now, is_today=True, is_travel=False, complete_until=None):
    # Default: mark everything before today as complete so tests see only
    # today's window lines; past-scan tests pass their own marker.
    db_connection.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('prayer_complete_until', ?)",
        (complete_until if complete_until is not None else TODAY_STR,),
    )
    db_connection.commit()
    monkeypatch.setattr(nudges, "is_travel_mode", lambda: is_travel)
    monkeypatch.setattr(nudges, "get_slot_windows", lambda *args, **kwargs: _fixed_windows())
    return nudges.get_prayer_nudges(db_connection, TARGET_DATE, TODAY_STR, is_today, now=now)


def _at(hour, minute=0, second=0):
    return datetime(2026, 9, 23, hour, minute, second)


def test_nudges_are_hidden_for_non_today(db_connection, monkeypatch):
    assert nudges.get_prayer_nudges(db_connection, TARGET_DATE, TODAY_STR, False) == []


def test_travel_mode_shows_first_unlogged_slot(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(9), is_travel=True)
    assert len(lines) == 1
    assert "Fajr not logged" in lines[0]
    db_connection.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES ('fajr', ?, 'on_time')",
        (TODAY_STR,),
    )
    db_connection.commit()
    lines = _nudges(db_connection, monkeypatch, _at(9), is_travel=True)
    assert "Dhuhr" in lines[0]


def test_prealert_under_one_hour_uses_em_dash(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(4, 0))
    prealert = [line for line in lines if "Fajr" in line]
    assert prealert == [f"{Y}🕌 Fajr — in ~31 min{RESET}"]


def test_prealert_reports_due_now_under_one_minute(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(4, 30, 30))
    assert any("Fajr — due now" in line for line in lines)


def test_no_prealert_more_than_an_hour_out(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(3, 0))
    assert not any("Fajr —" in line for line in lines)


def test_green_line_inside_fadilat(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(4, 40))
    assert lines == [f"{G}🕌 Fajr — until 05:55{RESET}"]


def test_yellow_line_between_fadilat_and_red(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(15, 30))
    assert f"{Y}🕌 Dhuhr & Asr — until 18:02{RESET}" in lines
    assert f"{R}⚠️ Fajr not logged (today){RESET}" in lines


def test_red_line_in_final_stretch(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(22, 0))
    assert f"{R}🕌 Maghrib & Isha — until 23:17{RESET}" in lines


def test_overdue_line_after_deadline(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(23, 30))
    for label in ("Fajr", "Dhuhr & Asr", "Maghrib & Isha"):
        assert f"{R}⚠️ {label} not logged (today){RESET}" in lines


def test_logged_slot_line_disappears(db_connection, monkeypatch):
    db_connection.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES ('fajr', ?, 'on_time')",
        (TODAY_STR,),
    )
    db_connection.commit()
    lines = _nudges(db_connection, monkeypatch, _at(4, 40))
    assert not any("Fajr" in line for line in lines)


def test_state_boundaries_are_exact(db_connection, monkeypatch):
    # Exactly at green_until the line turns yellow.
    assert _nudges(db_connection, monkeypatch, _at(4, 50)) == [f"{Y}🕌 Fajr — until 05:55{RESET}"]
    # Exactly at red_from the line turns red.
    assert _nudges(db_connection, monkeypatch, _at(5, 25)) == [f"{R}🕌 Fajr — until 05:55{RESET}"]
    # The minute-level deadline itself opens the overdue state.
    assert _nudges(db_connection, monkeypatch, _at(5, 55)) == [f"{R}⚠️ Fajr not logged (today){RESET}"]


def test_every_line_is_single_colored(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(22, 0))
    assert lines
    for line in lines:
        assert line.startswith(("\033[3", "⚠️")) or line[0] != "\033"
        if line.startswith("\033["):
            assert line.endswith(RESET)
            # Exactly one color code: no split coloring within a line.
            assert line.count("\033[3") == 1


def test_past_day_overdue_unchanged(db_connection, monkeypatch):
    # Freeze the completed-through marker so only 1405/06/31 is scanned.
    lines = _nudges(db_connection, monkeypatch, _at(4, 40), complete_until="1405-06-30")
    day_label = jdatetime.date(1405, 6, 31).strftime("%d %b")
    past = [line for line in lines if "not logged (" in line]
    assert past == [
        f"{R}⚠️ Fajr not logged ({day_label}){RESET}",
        f"{R}⚠️ Dhuhr & Asr not logged ({day_label}){RESET}",
        f"{R}⚠️ Maghrib & Isha not logged ({day_label}){RESET}",
    ]


def test_past_scan_respects_complete_until(db_connection, monkeypatch):
    lines = _nudges(db_connection, monkeypatch, _at(4, 40), complete_until="1405-06-31")
    assert lines == [f"{G}🕌 Fajr — until 05:55{RESET}"]


def test_past_scan_caps_at_five_lines(db_connection, monkeypatch):
    # No completion marker: the scan covers six past days of unlogged slots
    # but the overall nudge list is capped at five.
    lines = _nudges(db_connection, monkeypatch, _at(4, 40), complete_until="")
    assert len(lines) == 5
