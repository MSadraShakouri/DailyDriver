from dailydriver.display import header_renderer


def base_data(**overrides):
    data = {
        "jalali_line": "Jalali",
        "separator": "────",
        "greg_hijri_line": "Gregorian / Hijri",
        "feature_lines": [],
        "is_today": True,
        "last_entry_time": "",
    }
    data.update(overrides)
    return data


def test_renderer_prints_plain_and_structured_feature_lines(ui, monkeypatch):
    wrapped = []
    monkeypatch.setattr(header_renderer, "get_width", lambda: 80)
    monkeypatch.setattr(header_renderer, "pline", lambda line: ui.print_line(f"plain:{line}"))
    monkeypatch.setattr(header_renderer, "pline_center", lambda line: ui.print_line(f"center:{line}"))
    monkeypatch.setattr(
        header_renderer,
        "wrap_line",
        lambda prefix, title, indent: wrapped.append((prefix, title, indent)),
    )
    header_renderer.print_header(
        base_data(feature_lines=["weather", ("🔆 ", "A long calendar title")]),
        add_separator=False,
    )
    assert "plain:weather" in ui.lines
    assert wrapped == [("🔆 ", "A long calendar title", " " * 3)]


def test_renderer_bottom_bar_includes_last_entry_time(ui, monkeypatch):
    monkeypatch.setattr(header_renderer, "get_width", lambda: 80)
    monkeypatch.setattr(header_renderer, "pline", lambda line: None)
    monkeypatch.setattr(header_renderer, "pline_center", lambda line: None)
    header_renderer.print_header(base_data(last_entry_time="12:34"), add_separator=False)
    assert ui.lines[-1].endswith("Last 12:34")


def test_non_today_bottom_bar_omits_last_entry(ui, monkeypatch):
    monkeypatch.setattr(header_renderer, "get_width", lambda: 80)
    monkeypatch.setattr(header_renderer, "pline", lambda line: None)
    monkeypatch.setattr(header_renderer, "pline_center", lambda line: None)
    header_renderer.print_header(base_data(is_today=False, last_entry_time="12:34"), add_separator=False)
    assert "Last" not in ui.lines[-1]
