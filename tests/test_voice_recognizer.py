from __future__ import annotations

import threading
from voice.recognizer import BackendClient, CommandMapper, VoiceRecognizer


class DummyBackend(BackendClient):
    def __init__(self):
        self.calls = []

    def send_wake(self) -> None:
        self.calls.append(("wake", None, None))

    def send_command(self, command: str, payload: dict | None = None) -> None:
        self.calls.append(("command", command, payload))


def test_command_mapper_fixed_aliases_and_score():
    mapper = CommandMapper()
    assert mapper.to_backend_command("  Открыть   карту ") == "open_tasks_map"
    assert mapper.to_backend_command("режим проверки") == "open_day_review"
    assert mapper.to_backend_command("плохо") == "score_1"
    assert mapper.to_backend_command("не очень") == "score_2"
    assert mapper.to_backend_command("хорошо") == "score_3"
    assert mapper.to_backend_command("пропустить") == "score_skip"
    assert mapper.to_backend_command("оценка 2") is None
    assert mapper.to_backend_command("средне") is None
    assert mapper.to_backend_command("отлично") is None
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
        command_window_seconds=6.0,
    )

    thread = threading.Thread(target=recognizer.run_forever)
    thread.start()
    thread.join(timeout=2)

    assert backend.calls == [("wake", None, None), ("command", "open_tasks_map", None)]


def test_voice_flow_keeps_listening_for_6_seconds_after_command():
    phrases = iter(["плакат", "карта", "назад"])

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
        command_window_seconds=6.0,
    )

    thread = threading.Thread(target=recognizer.run_forever)
    thread.start()
    thread.join(timeout=2)

    assert backend.calls == [
        ("wake", None, None),
        ("command", "open_tasks_map", None),
        ("command", "back", None),
    ]


def test_default_audio_config_matches_test_voice_setup():
    recognizer = VoiceRecognizer()

    assert str(recognizer._model_path) == "/home/nq/EPoster/voice/vosk-model-small-ru-0.22"
    assert recognizer._input_device == 1
    assert recognizer._sample_rate == 48000
