from __future__ import annotations

import argparse
import json
import queue
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable


@dataclass
class VoiceCommand:
    text: str
    confidence: float = 1.0


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
            "плохо": "score_1",
            "средне": "score_2",
            "хорошо": "score_3",
            "отлично": "score_3",
            "праздник": "open_eid",
            "ид": "open_eid",
        }

    def normalize_text(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def to_backend_command(self, text: str) -> str | None:
        normalized = self.normalize_text(text)
        return self._aliases.get(normalized)


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
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            print(f"[voice] backend request failed {path}: {error}")
            return None

    def send_wake(self) -> None:
        self._post_json("/api/wake", {"source": "voice"})

    def send_command(self, command: str) -> None:
        self._post_json(
            "/api/command",
            {
                "command": command,
                "source": "voice",
                "wake_word_detected": True,
            },
        )


class VoiceRecognizer:
    """Offline-first voice module with wake word + fixed command set."""

    def __init__(
        self,
        wake_word: str = "плакат",
        command_window_seconds: float = 7.0,
        mapper: CommandMapper | None = None,
        backend: BackendClient | None = None,
        recognizer_fn: Callable[[], str | None] | None = None,
    ) -> None:
        self.wake_word = wake_word
        self.command_window_seconds = command_window_seconds
        self.mapper = mapper or CommandMapper()
        self.backend = backend or BackendClient()
        self._recognize_once = recognizer_fn or self._recognize_vosk
        self._stop_event = threading.Event()

    def _recognize_vosk(self) -> str | None:
        """Recognize speech chunk using vosk + sounddevice if available."""
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError:
            return None

        if not hasattr(self, "_vosk_model"):
            try:
                self._vosk_model = Model(lang="ru")
            except Exception as error:
                print(f"[voice] vosk model init failed: {error}")
                return None

        if not hasattr(self, "_audio_queue"):
            self._audio_queue = queue.Queue(maxsize=20)

        samplerate = 16000

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                return
            try:
                self._audio_queue.put_nowait(bytes(indata))
            except queue.Full:
                pass

        recognizer = KaldiRecognizer(self._vosk_model, samplerate)
        with sd.RawInputStream(
            samplerate=samplerate,
            blocksize=4000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            started = time.monotonic()
            while time.monotonic() - started < 2.3:
                if self._stop_event.is_set():
                    return None
                try:
                    data = self._audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = str(result.get("text", "")).strip()
                    if text:
                        return text
        partial = json.loads(recognizer.FinalResult())
        text = str(partial.get("text", "")).strip()
        return text or None

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
            print(f"[voice] recognized: {normalized}")

            if not wake_detected:
                if self.wake_word in normalized.split():
                    wake_detected = True
                    waiting_until = time.monotonic() + self.command_window_seconds
                    self.backend.send_wake()
                    print("[voice] wake word detected, command window open")
                continue

            command = self.mapper.to_backend_command(normalized)
            if command:
                self.backend.send_command(command)
                print(f"[voice] mapped command: {command}")
                wake_detected = False
                continue

            if time.monotonic() > waiting_until:
                wake_detected = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EPoster voice recognizer daemon")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--wake-word", default="плакат")
    parser.add_argument("--window", type=float, default=7.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recognizer = VoiceRecognizer(
        wake_word=args.wake_word,
        command_window_seconds=args.window,
        backend=BackendClient(args.backend_url),
    )
    try:
        recognizer.run_forever()
    except KeyboardInterrupt:
        recognizer.stop()


if __name__ == "__main__":
    main()
