from __future__ import annotations

import argparse
import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class BackendEvent:
    command: str
    payload: dict | None = None


class CommandMapper:
    """Maps fixed Russian phrases to backend commands."""

    def __init__(self) -> None:
        self._aliases = {
            "карта": "open_tasks_map",
            "открыть карту": "open_tasks_map",
            "открой карту": "open_tasks_map",
            "покажи карту": "open_tasks_map",
            "режим карты": "open_tasks_map",
            "проверка": "open_day_review",
            "режим проверки": "open_day_review",
            "открыть проверку": "open_day_review",
            "начать проверку": "open_day_review",
            "пропустить": "score_skip",
            "скип": "score_skip",
            "задание": "open_task_info",
            "открыть задание": "open_task_info",
            "открой задание": "open_task_info",
            "покажи задание": "open_task_info",
            "следующий": "next",
            "дальше": "next",
            "вперед": "next",
            "предыдущий": "prev",
            "раньше": "prev",
            "назад": "back",
            "вернуться": "back",
            "домой": "back",
            "ок": "ok",
            "подтвердить": "ok",
            "выбрать": "ok",
            "праздник": "open_eid",
            "ид": "open_eid",
        }

    def normalize_text(self, text: str) -> str:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.strip().split())

    def _extract_score_command(self, normalized: str) -> str | None:
        words = normalized.split()
        if "не" in words and "очень" in words:
            return "score_2"
        if "плохо" in words:
            return "score_1"
        if "хорошо" in words:
            return "score_3"
        if "пропустить" in words or "скип" in words:
            return "score_skip"
        return None

    def to_backend_command(self, text: str) -> str | None:
        normalized = self.normalize_text(text)
        score_command = self._extract_score_command(normalized)
        if score_command:
            return score_command
        return self._aliases.get(normalized)

    def to_backend_event(self, text: str) -> BackendEvent | None:
        command = self.to_backend_command(text)
        return BackendEvent(command=command) if command else None


class BackendClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base_url = base_url.rstrip("/")

    def _post_json(self, path: str, payload: dict) -> dict | None:
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload).encode("utf-8"),
        )
        try:
            with urllib.request.urlopen(req, timeout=2.5) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return None

    def send_wake(self) -> None:
        self._post_json("/api/wake", {"source": "voice"})

    def send_command(self, command: str, payload: dict | None = None) -> None:
        self._post_json(
            "/api/command",
            {
                "command": command,
                "payload": payload,
                "source": "voice",
                "wake_word_detected": True,
            },
        )


class VoiceRecognizer:
    """Voice module with wake word and fixed command set."""

    def __init__(
        self,
        wake_word: str = "плакат",
        command_window_seconds: float = 6.0,
        mapper: CommandMapper | None = None,
        backend: BackendClient | None = None,
        recognizer_fn: Callable[[], str | None] | None = None,
        model_path: str = "/home/nq/EPoster/voice/vosk-model-small-ru-0.22",
        input_device: int = 1,
        sample_rate: int = 48000,
    ) -> None:
        self.wake_word = wake_word
        self.command_window_seconds = command_window_seconds
        self.mapper = mapper or CommandMapper()
        self.backend = backend or BackendClient()
        self._recognize_once = recognizer_fn or self._recognize_vosk
        self._stop_event = threading.Event()
        self._model_path = Path(model_path).expanduser()
        self._input_device = input_device
        self._sample_rate = sample_rate
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

    def _recognize_vosk(self) -> str | None:
        try:
            import sounddevice as sd
            import vosk
        except ImportError:
            time.sleep(0.3)
            return None

        if not hasattr(self, "_vosk_model"):
            self._vosk_model = vosk.Model(str(self._model_path))

        recognizer = vosk.KaldiRecognizer(self._vosk_model, self._sample_rate)

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                return
            self._audio_queue.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=8000,
            device=self._input_device,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while not self._stop_event.is_set():
                try:
                    data = self._audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = str(result.get("text", "")).strip()
                    if text:
                        return text

        return None

    def stop(self) -> None:
        self._stop_event.set()

    def run_forever(self) -> None:
        waiting_until = 0.0
        wake_detected = False

        while not self._stop_event.is_set():
            phrase = self._recognize_once()
            if not phrase:
                time.sleep(0.05)
                if wake_detected and time.monotonic() > waiting_until:
                    wake_detected = False
                continue

            normalized = self.mapper.normalize_text(phrase)

            if not wake_detected:
                if self.wake_word in normalized.split():
                    wake_detected = True
                    waiting_until = time.monotonic() + self.command_window_seconds
                    self.backend.send_wake()
                continue

            command = self.mapper.to_backend_command(normalized)
            if command:
                self.backend.send_command(command)
                waiting_until = time.monotonic() + self.command_window_seconds
                continue

            if time.monotonic() > waiting_until:
                wake_detected = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EPoster voice recognizer daemon")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--wake-word", default="плакат")
    parser.add_argument("--window", type=float, default=6.0)
    parser.add_argument("--model-path", default="/home/nq/EPoster/voice/vosk-model-small-ru-0.22")
    parser.add_argument("--input-device", type=int, default=1)
    parser.add_argument("--sample-rate", type=int, default=48000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recognizer = VoiceRecognizer(
        wake_word=args.wake_word,
        command_window_seconds=args.window,
        backend=BackendClient(args.backend_url),
        model_path=args.model_path,
        input_device=args.input_device,
        sample_rate=args.sample_rate,
    )
    try:
        recognizer.run_forever()
    except KeyboardInterrupt:
        recognizer.stop()


if __name__ == "__main__":
    main()
