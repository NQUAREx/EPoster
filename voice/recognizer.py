from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VoiceCommand:
    text: str
    confidence: float = 1.0


class VoiceRecognizer:
    """Lightweight recognizer for fixed commands.

    Реального STT здесь нет: модуль принимает уже распознанный текст (или симулированный текст)
    и нормализует его к фиксированным командам приложения.
    """

    def __init__(self):
        self._queue: list[VoiceCommand] = []
        self._aliases = {
            "открыть карту": "open_map",
            "карта": "open_map",
            "итоги": "open_summary",
            "настройки": "open_settings",
            "завершить день": "finish_day",
            "следующий день": "next_day",
            "назад": "back",
            "перезапуск": "restart",
        }

    def push_simulated(self, text: str, confidence: float = 1.0) -> None:
        normalized = self.normalize_text(text)
        self._queue.append(VoiceCommand(text=normalized, confidence=confidence))

    def normalize_text(self, text: str) -> str:
        key = " ".join(text.lower().strip().split())
        return self._aliases.get(key, key)

    def listen(self) -> VoiceCommand | None:
        if not self._queue:
            return None
        return self._queue.pop(0)
