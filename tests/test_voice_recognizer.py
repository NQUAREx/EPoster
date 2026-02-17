from __future__ import annotations

import threading

from voice.recognizer import BackendClient, CommandMapper, VoiceRecognizer


class DummyBackend(BackendClient):
    def __init__(self):
        self.calls = []

    def send_wake(self) -> None:
        self.calls.append(("wake", None))

    def send_command(self, command: str) -> None:
        self.calls.append(("command", command))


def test_command_mapper_fixed_aliases():
    mapper = CommandMapper()
    assert mapper.to_backend_command("  Открыть   карту ") == "open_tasks_map"
    assert mapper.to_backend_command("режим проверки") == "open_day_review"
    assert mapper.to_backend_command("отлично") == "score_3"
    assert mapper.to_backend_command("неизвестно") is None


def test_voice_flow_wake_then_command():
    phrases = iter(["плакат", "карта"])

    def recognize_once():
        try:
            return next(phrases)
        except StopIteration:
            recognizer.stop()
            return None

    backend = DummyBackend()
    recognizer = VoiceRecognizer(
        backend=backend,
        recognizer_fn=recognize_once,
        command_window_seconds=7.0,
    )

    thread = threading.Thread(target=recognizer.run_forever)
    thread.start()
    thread.join(timeout=2)

    assert backend.calls == [("wake", None), ("command", "open_tasks_map")]
