from __future__ import annotations

import hardware.cursor as cursor


class _FakeMouse:
    def __init__(self, calls: dict):
        self._calls = calls

    def set_visible(self, value):
        self._calls["set_visible"].append(value)


class _FakePygame:
    def __init__(self, calls: dict):
        self._calls = calls
        self.mouse = _FakeMouse(calls)

    def init(self):
        self._calls["init"] += 1


def test_move_cursor_hides_cursor(monkeypatch):
    cursor._CURSOR_HIDDEN = False
    calls = {"init": 0, "set_visible": []}

    monkeypatch.setattr(cursor.importlib, "import_module", lambda name: _FakePygame(calls))

    assert cursor.move_cursor_to_bottom_right() is True
    assert calls["init"] == 1
    assert calls["set_visible"] == [False]


def test_move_cursor_reuses_hidden_state(monkeypatch):
    cursor._CURSOR_HIDDEN = True
    called = {"value": False}

    def _never_call(_name):
        called["value"] = True
        raise AssertionError("import_module should not be called")

    monkeypatch.setattr(cursor.importlib, "import_module", _never_call)

    assert cursor.move_cursor_to_bottom_right() is True
    assert called["value"] is False
