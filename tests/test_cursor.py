from __future__ import annotations

import hardware.cursor as cursor


def test_move_cursor_returns_false_without_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    cursor._UNCLUTTER_PROCESS = None

    assert cursor.move_cursor_to_bottom_right() is False


def test_move_cursor_starts_unclutter(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    cursor._UNCLUTTER_PROCESS = None

    class _FakeProcess:
        def poll(self):
            return None

    started = {}

    def _fake_popen(cmd, stdout, stderr, start_new_session):
        started["cmd"] = cmd
        started["start_new_session"] = start_new_session
        return _FakeProcess()

    monkeypatch.setattr("subprocess.Popen", _fake_popen)

    assert cursor.move_cursor_to_bottom_right() is True
    assert started["cmd"] == ["unclutter", "-idle", "0"]
    assert started["start_new_session"] is True


def test_move_cursor_reuses_running_unclutter(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")

    class _FakeProcess:
        def poll(self):
            return None

    cursor._UNCLUTTER_PROCESS = _FakeProcess()

    called = {"value": False}

    def _never_call(*args, **kwargs):
        called["value"] = True
        raise AssertionError("Popen should not be called")

    monkeypatch.setattr("subprocess.Popen", _never_call)

    assert cursor.move_cursor_to_bottom_right() is True
    assert called["value"] is False
