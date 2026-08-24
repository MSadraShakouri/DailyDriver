from datetime import datetime, timedelta
from unittest.mock import Mock

from dailydriver.core.journal import logger
from dailydriver.utils.time_parser import TimeInterpretation


def interpretation(hour=9, duration=30, label="09:00 → 09:30"):
    start = datetime(2026, 8, 23, hour)
    return TimeInterpretation(start, start + timedelta(minutes=duration), duration, label, 0)


def prepare(monkeypatch, interpretations):
    save = Mock(return_value="saved")
    monkeypatch.setattr(logger, "parse_time_expressions", lambda *args: interpretations)
    monkeypatch.setattr(logger, "find_matching_categories", lambda command, limit=None: [])
    monkeypatch.setattr(logger, "inject_great_categories", Mock())
    monkeypatch.setattr(logger, "save_entry", save)
    monkeypatch.setattr(logger, "get_active_great_event", lambda: None)
    return save


def test_single_interpretation_is_confirmed_and_saved(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    ui.queue("")
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
    ui.queue("", "")
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
    monkeypatch.setattr(
        logger, "find_matching_categories", lambda command, limit=None: [("work/code", 1), ("work/review", 0.5)]
    )
    ui.queue("2 custom/path")
    logger.log_free_text("09:00-09:30 work")
    assert save.call_args.args[4] == ["work/review", "custom/path"]


def test_great_event_only_option_clears_regular_selection(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    monkeypatch.setattr(
        logger, "find_matching_categories", lambda command, limit=None: [("work/code", 1), ("work/review", 0.5)]
    )
    monkeypatch.setattr(logger, "get_active_great_event", lambda: (1, ["deep/work"]))
    ui.queue("0")
    logger.log_free_text("09:00-09:30 work")
    assert save.call_args.args[4] == []
    assert any("Great Event only" in line for line in ui.lines)


def test_auto_selected_time_can_be_rejected(db_path, ui, monkeypatch):
    save = prepare(monkeypatch, [interpretation()])
    monkeypatch.setattr(logger.current_ui, "confirm_time", lambda *args: False)
    assert logger.log_free_text("09:00-09:30 work") is None
    save.assert_not_called()


def test_rich_picker_result_is_used_and_new_paths_persisted(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    monkeypatch.setattr(logger, "find_matching_categories", lambda command, limit=None: [("work/code", 1)])
    # Simulate a rich backend returning an explicit selection including a new path.
    monkeypatch.setattr(logger.current_ui, "select_categories", lambda *a, **k: ["work/code", "fresh/topic"])
    logger.log_free_text("09:00-09:30 work")
    assert save.call_args.args[4] == ["work/code", "fresh/topic"]
    # The brand-new path must have been persisted to the categories table.
    from dailydriver.core.database import get_connection_cm

    with get_connection_cm() as conn:
        paths = {row["path"] for row in conn.execute("SELECT path FROM categories")}
    assert "fresh/topic" in paths


def test_plain_flow_used_when_picker_returns_none(db_path, ui, monkeypatch):
    selected = interpretation()
    save = prepare(monkeypatch, [selected])
    monkeypatch.setattr(
        logger, "find_matching_categories", lambda command, limit=None: [("work/code", 1), ("work/review", 0.5)]
    )
    # Default TerminalUI.select_categories returns None -> plain numbered flow.
    monkeypatch.setattr(logger.current_ui, "select_categories", lambda *a, **k: None)
    ui.queue("2")
    logger.log_free_text("09:00-09:30 work")
    assert save.call_args.args[4] == ["work/review"]
