from dailydriver.features.weather import provider


class Response:
    def __init__(self, html):
        self.html = html

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.html.encode()


def test_fetch_parses_persian_temperature_and_condition(monkeypatch):
    html = 'هوای حاضر<div style="font-size:48px">۲۸° c </div><div style="font-size:18px">صاف</div>'
    monkeypatch.setattr(provider.urllib.request, "urlopen", lambda *args, **kwargs: Response(html))
    assert provider.fetch_weather() == (28, "صاف")


def test_fetch_returns_none_for_network_and_parse_failures(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(provider.urllib.request, "urlopen", fail)
    assert provider.fetch_weather() is None
    monkeypatch.setattr(provider.urllib.request, "urlopen", lambda *args, **kwargs: Response("no weather"))
    assert provider.fetch_weather() is None
