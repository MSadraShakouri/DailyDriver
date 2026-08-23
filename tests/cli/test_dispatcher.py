from unittest.mock import patch

from dailydriver.cli.commands.events import log_chain_now, log_event_end, start_great_event_cmd
from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.search import search
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.features.prayer.commands import log_prayer
from dailydriver.features.sleep.commands import log_nap, log_sleep



def test_core_and_feature_commands_share_dispatch_table():
    dispatch = make_dispatch()
    assert dispatch["export"] is export
    assert dispatch["search"] is search
    assert dispatch["p"] is log_prayer
    assert dispatch["s"] is log_sleep
    assert dispatch["nap"] is log_nap
    assert dispatch["ee"] is log_event_end
    assert dispatch["ln"] is log_chain_now
    assert dispatch["sge"] is start_great_event_cmd



def test_view_forwards_optional_argument():
    with patch("dailydriver.cli.dispatcher.view_entries") as view:
        dispatch = make_dispatch()
        dispatch["view"]("view 7d")
        dispatch["view"]("view")
    assert view.call_args_list[0].args == ("7d",)
    assert view.call_args_list[1].args == (None,)



def test_every_enabled_feature_can_register_commands(monkeypatch):
    called = []

    def hook(feature):
        register = getattr(feature, "register_commands", None)
        if register:
            called.append(feature.NAME)
        return register

    monkeypatch.setattr("dailydriver.cli.dispatcher.command_hook", hook)
    make_dispatch()
    assert {"birthdays", "calendar", "intentions", "prayer", "qada", "sleep", "targets", "void"} <= set(called)
