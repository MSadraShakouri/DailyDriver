"""Cross-package command registration smoke tests without import-time side effects."""

import inspect

from dailydriver.cli.dispatcher import make_dispatch



def test_every_registered_handler_accepts_raw_command_line():
    failures = []
    for name, handler in make_dispatch().items():
        if name == "q":
            continue
        try:
            inspect.signature(handler).bind("test")
        except TypeError as error:
            failures.append(f"{name}: {error}")
    assert failures == []



def test_expected_commands_and_aliases_are_registered():
    dispatch = make_dispatch()
    expected = {
        "?",
        "bd",
        "birthdays",
        "cal",
        "ce",
        "cge",
        "ee",
        "ege",
        "habit",
        "hijri",
        "hygiene",
        "ln",
        "nap",
        "nazr",
        "p",
        "pray",
        "qada",
        "s",
        "se",
        "sge",
        "sleep",
        "targets",
        "today",
        "travel",
        "u",
        "update",
        "v",
        "void",
        "vexport",
        "year",
    }
    assert expected <= dispatch.keys()
    assert dispatch["pray"] is dispatch["p"]
    assert dispatch["sleep"] is dispatch["s"]



def test_feature_handlers_are_owned_by_feature_modules():
    dispatch = make_dispatch()
    assert dispatch["p"].__module__ == "dailydriver.features.prayer.commands"
    assert dispatch["nap"].__module__ == "dailydriver.features.sleep.commands"
    assert dispatch["qada"].__module__ == "dailydriver.features.qada.commands"
    assert dispatch["ee"].__module__ == "dailydriver.cli.commands.events"
