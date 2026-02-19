from __future__ import annotations

import argparse
import json
import os
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
class VoiceCommand:
    text: str
    confidence: float = 1.0


@dataclass
class BackendEvent:
    command: str
    payload: dict | None = None


class CommandMapper:
    """Maps fixed Russian phrases to backend commands with optional payload."""

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
            "праздник": "open_eid",
            "ид": "open_eid",
        }

    def normalize_text(self, text: str) -> str:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.strip().split())

    def _extract_score_command(self, normalized: str) -> str | None:
        words = normalized.split()
        if not words:
            return None

        if "не" in words and "очень" in words:
            return "score_2"

        for token in words:
            if token == "плохо":
                return "score_1"
            if token == "хорошо":
                return "score_3"

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
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            print(f"[voice] backend request failed {path}: {error}")
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
    """Offline-first voice module with wake word + fixed command set."""

    def __init__(
        self,
        wake_word: str = "плакат",
        command_window_seconds: float = 6.0,
        mapper: CommandMapper | None = None,
        backend: BackendClient | None = None,
        recognizer_fn: Callable[[], str | None] | None = None,
        model_path: str | None = None,
        input_device: int | str | None = None,
    ) -> None:
        self.wake_word = wake_word
        self.command_window_seconds = command_window_seconds
        self.mapper = mapper or CommandMapper()
        self.backend = backend or BackendClient()
        self._recognize_once = recognizer_fn or self._recognize_vosk
        self._stop_event = threading.Event()
        self._model_path = model_path
        self._vosk_disabled = False
        self._input_device = input_device

    @staticmethod
    def _is_valid_model_dir(path: Path) -> bool:
        return (path / "am" / "final.mdl").exists() and (path / "conf" / "model.conf").exists()

    def _resolve_model_path(self) -> Path | None:
        candidates: list[Path] = []
        if self._model_path:
            candidates.append(Path(self._model_path).expanduser())
        env_path = os.getenv("VOSK_MODEL_PATH")
        if env_path:
            candidates.append(Path(env_path).expanduser())

        home = Path.home()
        candidates.extend(
            [
                home / ".cache" / "vosk" / "vosk-model-small-ru-0.22",
                home / ".cache" / "vosk-model-small-ru-0.22",
                home / "AppData" / "Local" / "vosk" / "vosk-model-small-ru-0.22",
            ]
        )

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_dir() and self._is_valid_model_dir(resolved):
                return resolved
        return None

    @staticmethod
    def _samplerate_candidates(default_samplerate: float | int | None) -> list[int]:
        candidates: list[int] = []
        if default_samplerate is not None:
            try:
                candidates.append(int(round(float(default_samplerate))))
            except (TypeError, ValueError):
                pass

        for samplerate in (16000, 8000, 4000, 48000, 44100, 32000):
            if samplerate not in candidates:
                candidates.append(samplerate)
        return candidates

    @classmethod
    def _pick_supported_samplerate(
        cls,
        check_input_settings: Callable[..., None],
        default_samplerate: float | int | None,
        device: int | str | None,
    ) -> list[int]:
        candidates = cls._samplerate_candidates(default_samplerate)
        supported: list[int] = []
        for samplerate in candidates:
            try:
                check_input_settings(
                    device=device,
                    samplerate=samplerate,
                    channels=1,
                    dtype="int16",
                )
                supported.append(samplerate)
            except Exception:
                continue

        if supported:
            return supported

        target = f"device={device}" if device is not None else "default input device"
        tried = ", ".join(str(item) for item in candidates)
        raise RuntimeError(f"No supported sample rate for {target}. Tried: {tried}")

    def _resolve_input_device(self):
        if self._input_device is not None:
            return self._input_device

        env_value = os.getenv("VOICE_INPUT_DEVICE")
        if not env_value:
            return None

        try:
            return int(env_value)
        except ValueError:
            return env_value

    def _recognize_vosk(self) -> str | None:
        """Recognize speech chunk using vosk + sounddevice if available."""
        if self._vosk_disabled:
            time.sleep(0.3)
            return None

        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError:
            self._vosk_disabled = True
            print("[voice] install vosk and sounddevice to enable STT")
            return None

        if not hasattr(self, "_vosk_model"):
            model_dir = self._resolve_model_path()
            if model_dir is None:
                self._vosk_disabled = True
                print(
                    "[voice] vosk model not found or invalid. "
                    "Set --model-path or VOSK_MODEL_PATH to a valid model directory"
                )
                return None
            try:
                self._vosk_model = Model(str(model_dir))
                print(f"[voice] using vosk model: {model_dir}")
            except Exception as error:
                self._vosk_disabled = True
                print(f"[voice] vosk model init failed: {error}")
                return None

        if not hasattr(self, "_audio_queue"):
            self._audio_queue = queue.Queue(maxsize=20)

        input_device = self._resolve_input_device()
        device_info = sd.query_devices(input_device, "input") if input_device is not None else sd.query_devices(kind="input")
        supported_samplerates = self._pick_supported_samplerate(
            check_input_settings=sd.check_input_settings,
            default_samplerate=device_info.get("default_samplerate"),
            device=input_device,
        )

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                return
            try:
                self._audio_queue.put_nowait(bytes(indata))
            except queue.Full:
                pass

        for samplerate in supported_samplerates:
            if input_device is not None:
                print(f"[voice] trying input device={input_device}, samplerate={samplerate}")
            else:
                print(f"[voice] trying input samplerate={samplerate}")

            recognizer = KaldiRecognizer(self._vosk_model, samplerate)
            try:
                with sd.RawInputStream(
                    device=input_device,
                    samplerate=samplerate,
                    blocksize=0,
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
            except sd.PortAudioError as error:
                if "Invalid sample rate" in str(error):
                    continue
                raise

            result = json.loads(recognizer.FinalResult())
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
            print(f"[voice] recognized: {phrase}")
            print(f"[voice] normalized: {normalized}")

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
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--input-device", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recognizer = VoiceRecognizer(
        wake_word=args.wake_word,
        command_window_seconds=args.window,
        backend=BackendClient(args.backend_url),
        model_path=args.model_path,
        input_device=int(args.input_device) if isinstance(args.input_device, str) and args.input_device.isdigit() else args.input_device,
    )
    try:
        recognizer.run_forever()
    except KeyboardInterrupt:
        recognizer.stop()


if __name__ == "__main__":
    main()
