from datetime import datetime, timedelta
from unittest.mock import Mock

from dailydriver.core import logger
from dailydriver.utils.time_parser import TimeInterpretation


def interpretation(hour=9, duration=30, label="09:00 → 09:30"):
    start = datetime(2026, 8, 23, hour)
    return TimeInterpretation(start, start + timedelta(minutes=duration), duration, label, 0)


def prepare(monkeypatch, interpretations):
    save = Mock(return_value="saved")
    monkeypatch.setattr(logger, "parse_time_expressions", lambda *args: interpretations)
    monkeypatch.setattr(logger, "find_matching_categories", lambda command: [])
    monkeypatch.setattr(logger, "inject_great_categories", Mock())
    monkeypatch.setattr(logger, "_save_entry", save)
    return save


def test_single_interpretation_is_confirmed_and_saved(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    ui.queue("")  # category prompt
    assert logger.log_free_text("09:00-09:30 work") == "saved"
    args = save.call_args.args
    assert args[2] == int(selected.start.timestamp())
    assert args[3] == 30
    assert args[4] == []


def test_multiple_interpretations_use_explicit_selection_without_confirmation(db_path, ui, monkeypatch):
    first = interpretation(9)
    second = interpretation(21, label="21:00 → 21:30")
    save = prepare(monkeypatch, [first, second])
    confirmations = []
    monkeypatch.setattr(logger.current_ui, "confirm_time", lambda *args: confirmations.append(args) or True)
    ui.queue("2", "")
    logger.log_free_text("9-9:30 work")
    assert save.call_args.args[2] == int(second.start.timestamp())
    assert confirmations == []


def test_no_detected_time_can_use_now(db_path, ui, monkeypatch):
    save = prepare(monkeypatch, [])
    ui.queue("", "")  # use now, skip category
    logger.log_free_text("plain entry")
    assert isinstance(save.call_args.args[2], int)
    assert save.call_args.args[3] is None
    assert "No time detected." in ui.lines


def test_time_selection_can_cancel(db_path, ui, monkeypatch):
    save = prepare(monkeypatch, [])
    ui.queue("n")
    assert logger.log_free_text("plain entry") is None
    save.assert_not_called()


def test_chained_entry_honors_confirmation(db_path, ui, monkeypatch):
    save = prepare(monkeypatch, [])
    monkeypatch.setattr(logger.current_ui, "confirm_time", lambda *args: False)
    assert logger.log_free_text("chained", started_at=int(datetime.now().timestamp()) - 60) is None
    save.assert_not_called()


def test_suggested_categories_support_numbers_and_new_paths(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    monkeypatch.setattr(logger, "find_matching_categories", lambda command: [("work/code", 1), ("work/review", 0.5)])
    ui.queue("2 custom/path")
    logger.log_free_text("09:00-09:30 work")
    assert save.call_args.args[4] == ["work/review", "custom/path"]


def test_auto_selected_time_can_be_rejected(db_path, ui, monkeypatch):
    save = prepare(monkeypatch, [interpretation()])
    monkeypatch.setattr(logger.current_ui, "confirm_time", lambda *args: False)
    assert logger.log_free_text("09:00-09:30 work") is None
    save.assert_not_called()
