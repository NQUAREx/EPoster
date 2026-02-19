from __future__ import annotations

import threading
from pathlib import Path

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


def test_vosk_model_validation(tmp_path: Path):
    recognizer = VoiceRecognizer(model_path=str(tmp_path))
    assert recognizer._resolve_model_path() is None

    model_dir = tmp_path / "vosk-model-small-ru-0.22"
    (model_dir / "am").mkdir(parents=True)
    (model_dir / "conf").mkdir(parents=True)
    (model_dir / "am" / "final.mdl").write_text("x")
    (model_dir / "conf" / "model.conf").write_text("x")

    recognizer = VoiceRecognizer(model_path=str(model_dir))
    resolved = recognizer._resolve_model_path()
    assert resolved == model_dir.resolve()


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


def test_default_audio_config_is_fixed_for_known_microphone(monkeypatch):
    monkeypatch.delenv("VOICE_INPUT_DEVICE", raising=False)
    monkeypatch.delenv("VOICE_SAMPLERATE", raising=False)

    recognizer = VoiceRecognizer()

    assert recognizer._resolve_input_device() == "plughw:2,0"
    assert recognizer._resolve_samplerate() == 4000


def test_audio_config_can_be_overridden(monkeypatch):
    monkeypatch.setenv("VOICE_INPUT_DEVICE", "7")
    monkeypatch.setenv("VOICE_SAMPLERATE", "8000")

    recognizer = VoiceRecognizer()

    assert recognizer._resolve_input_device() == 7
    assert recognizer._resolve_samplerate() == 8000
