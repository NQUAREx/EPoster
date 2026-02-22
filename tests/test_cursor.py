from __future__ import annotations

from types import SimpleNamespace

from hardware.cursor import move_cursor_to_bottom_right


class _FakePyAutoGui:
    def __init__(self) -> None:
        self.moved = None

    def size(self):
        return (1920, 1080)

    def moveTo(self, x, y, duration=0):
        self.moved = (x, y, duration)


def test_move_cursor_returns_false_when_pyautogui_missing(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)

    assert move_cursor_to_bottom_right() is False


def test_move_cursor_moves_to_bottom_right(monkeypatch):
    fake = _FakePyAutoGui()
    monkeypatch.setattr("importlib.util.find_spec", lambda name: SimpleNamespace())
    monkeypatch.setattr("importlib.import_module", lambda name: fake)

    assert move_cursor_to_bottom_right() is True
    assert fake.moved == (1919, 1079, 0)
